# Copyright 2019 TerraPower, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tests for lumpedFissionProduce module
"""
import unittest
import io

from armi.physics.neutronics.fissionProductModel import lumpedFissionProduct
from armi.nucDirectory import nuclideBases

LFP_TEXT = """        13          LFP35 GE73 5  5.9000E-06
        13          LFP35 GE74 5  1.4000E-05
        13          LFP35 GE76 5  1.6000E-04
        13          LFP35 AS75 5  8.9000E-05
        13          LFP35 KR85 5  8.9000E-05
        13          LFP35 MO99 5  8.9000E-05
        13          LFP35 SM1505  8.9000E-05
        13          LFP35 XE1355  8.9000E-05
        13          LFP39 XE1355  8.9000E-05
        13          LFP38 XE1355  8.9000E-05
"""


def getDummyLFPFile():
    return lumpedFissionProduct.FissionProductDefinitionFile(io.StringIO(LFP_TEXT))


class TestFissionProductDefinitionFile(unittest.TestCase):
    """ Test of the fission product model """

    def setUp(self):
        self.fpd = getDummyLFPFile()

    def testCreateLFPs(self):
        """ Test of the fission product model creation """
        lfps = self.fpd.createLFPsFromFile()
        xe135 = nuclideBases.fromName("XE135")
        self.assertEqual(len(lfps), 3)
        self.assertIn("LFP35", lfps)
        for lfp in lfps.values():
            self.assertIn(xe135, lfp)


class TestLumpedFissionProduct(unittest.TestCase):
    """ Test of the lumped fission product yields """

    def setUp(self):
        self.fpd = lumpedFissionProduct.FissionProductDefinitionFile(
            io.StringIO(LFP_TEXT)
        )

    def test_setGasRemovedFrac(self):
        """ Test of the set gas removal fraction """
        lfp = self.fpd.createSingleLFPFromFile("LFP38")
        xe135 = nuclideBases.fromName("XE135")
        gas1 = lfp[xe135]
        lfp.setGasRemovedFrac(0.25)
        gas2 = lfp[xe135]
        self.assertAlmostEqual(gas1 * 0.75, gas2)

    def test_getYield(self):
        """ Test of the yield of a fission product """
        xe135 = nuclideBases.fromName("XE135")
        lfp = self.fpd.createSingleLFPFromFile("LFP39")
        lfp[xe135] = 3
        val3 = lfp[xe135]
        self.assertEqual(val3, 3)
        self.assertIsNone(lfp[5])

    def test_getGasFraction(self):
        """ Test of the get gas removal fraction """
        lfp = self.fpd.createSingleLFPFromFile("LFP35")
        frac = lfp.getGasFraction()
        self.assertGreater(frac, 0.0)
        self.assertLess(frac, 1.0)

    def test_getLanthanideFraction(self):
        """ Test of the lanthanide fraction function """
        lfp = self.fpd.createSingleLFPFromFile("LFP35")
        frac = lfp.getLanthanideFraction()
        self.assertGreater(frac, 0.0)
        self.assertLess(frac, 1.0)


class TestLumpedFissionProductCollection(unittest.TestCase):
    """ Test of the fission product collection """

    def setUp(self):
        fpd = lumpedFissionProduct.FissionProductDefinitionFile(io.StringIO(LFP_TEXT))
        self.lfps = fpd.createLFPsFromFile()

    def test_getAllFissionProductNames(self):
        """ Test to ensure the fission product names are present """
        names = self.lfps.getAllFissionProductNames()
        self.assertIn("XE135", names)
        self.assertIn("KR85", names)

    def test_duplicate(self):
        """ Test to ensure that when we duplicate, we don't adjust the original file """
        newLfps = self.lfps.duplicate()
        ba = nuclideBases.fromName("XE135")
        lfp1 = self.lfps["LFP39"]
        lfp2 = newLfps["LFP39"]
        v1 = lfp1[ba]
        lfp1[ba] += 5.0  # make sure copy doesn't change w/ first.
        v2 = lfp2[ba]
        self.assertEqual(v1, v2)


class TestMo99LFP(unittest.TestCase):
    """ Test of the fission product model from Mo99 """

    def setUp(self):
        self.lfps = (
            lumpedFissionProduct._buildMo99LumpedFissionProduct()
        )  # pylint: disable=protected-access

    def test_getAllFissionProductNames(self):
        """ Test to ensure that Mo99 is present, but other FP are not """
        names = self.lfps.getAllFissionProductNames()
        self.assertIn("MO99", names)
        self.assertNotIn("KR85", names)
        self.assertAlmostEqual(self.lfps["LFP35"].getTotalYield(), 2.0)


class TestExpandCollapse(unittest.TestCase):
    """ Test of the ability of the fission product file to expand from the LFPs """

    def test_expand(self):

        fpd = lumpedFissionProduct.FissionProductDefinitionFile(io.StringIO(LFP_TEXT))
        lfps = fpd.createSingleLFPCollectionFromFile("LFP35")

        massFrac = {
            "U238": 24482008.501781337,
            "LFP35": 0.0,
            "CL35": 1617.0794376133247,
            "CL37": 17091083.486970097,
            "U235": 3390057.9136671578,
            "NA23": 367662.29994516558,
        }
        refMassFrac = massFrac.copy()
        del refMassFrac["LFP35"]
        testMassFrac = lumpedFissionProduct.expandFissionProducts(massFrac, {})

        for nucName, mass in refMassFrac.items():
            normalizedMass = (testMassFrac[nucName] - mass) / mass
            self.assertAlmostEqual(normalizedMass, 0, 6)

        refMassFrac = lfps.getFirstLfp().getMassFracs()
        massFrac = {lfps.getFirstLfp().name: 1}
        newMassFrac = lumpedFissionProduct.expandFissionProducts(massFrac, lfps)

        for nb, mass in refMassFrac.items():
            normalizedMass = (newMassFrac[nb.name] - mass) / mass
            self.assertAlmostEqual(normalizedMass, 0, 6)

    def test_collapse(self):

        fpd = lumpedFissionProduct.FissionProductDefinitionFile(io.StringIO(LFP_TEXT))
        lfps = fpd.createSingleLFPCollectionFromFile("LFP35")

        burnup = 0.01  # fima

        # make 1% burnup fuel
        refMassFracs = {"U235": 1 - burnup}

        lfp = lfps.getFirstLfp()
        for nb, mFrac in lfp.getMassFracs().items():
            refMassFracs[nb.name] = burnup * mFrac

        newMassFracs = lumpedFissionProduct.collapseFissionProducts(refMassFracs, lfps)

        self.assertAlmostEqual(newMassFracs["LFP35"], burnup, 6)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

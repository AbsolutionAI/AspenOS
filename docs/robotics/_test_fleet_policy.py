#!/usr/bin/env python3
"""ASP-416 G6: fleet_policy cross-plant ACL test (called as subprocess)."""
import sys
sys.path.insert(0, sys.argv[1])

import fleet_policy
fleet_policy.clear_cache()

# Test 1: plant-range -> plant-alpha denied
r1 = fleet_policy.check_cross_plant("plant-range", "plant-alpha")
print("RANGE_TO_ALPHA:" + ("denied" if r1 else "allowed") + "|" + (r1 or ""))

# Test 2: plant-alpha -> plant-edge allowed by fleet.yaml ACL
r2 = fleet_policy.check_cross_plant("plant-alpha", "plant-edge")
print("ALPHA_TO_EDGE:" + ("denied" if r2 else "allowed") + "|" + (r2 or ""))

# Test 3: plant-alpha -> plant-range denied (target isolated)
r3 = fleet_policy.check_cross_plant("plant-alpha", "plant-range")
print("ALPHA_TO_RANGE:" + ("denied" if r3 else "allowed") + "|" + (r3 or ""))

# Test 4: same-plant allowed
r4 = fleet_policy.check_cross_plant("plant-range", "plant-range")
print("SAME_PLANT:" + ("denied" if r4 else "allowed") + "|" + (r4 or ""))
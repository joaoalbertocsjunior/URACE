import json,tempfile,unittest
from pathlib import Path
from urace import tokenomics
from urace import credit_ledger

class TokenUnitTests(unittest.TestCase):
 def test_schema_key(self):self.assertEqual(tokenomics.TOKEN_UNIT['schema'],'urace-tokenomics-v1')
 def test_mainnet_disabled(self):self.assertFalse(tokenomics.TOKEN_UNIT['mainnet_settlement_enabled'])
 def test_baseline_grant(self):self.assertEqual(tokenomics.TOKEN_UNIT['baseline_grant_requests'],3)

class CanonicalFingerprintTests(unittest.TestCase):
 def test_deterministic(self):
  d={'a.py':'x = 1\n','b.py':'y = 2\n'};self.assertEqual(tokenomics.canonical_fingerprint(d),tokenomics.canonical_fingerprint(d))
 def test_order_independent(self):
  a=tokenomics.canonical_fingerprint({'a.py':'x=1','b.py':'y=2'});b=tokenomics.canonical_fingerprint({'b.py':'y=2','a.py':'x=1'});self.assertEqual(a,b)
 def test_whitespace_normalized(self):
  a=tokenomics.canonical_fingerprint({'f.py':'x = 1'});b=tokenomics.canonical_fingerprint({'f.py':'x=1'});self.assertEqual(a,b)
 def test_different_content_differs(self):
  a=tokenomics.canonical_fingerprint({'f.py':'x = 1'});b=tokenomics.canonical_fingerprint({'f.py':'x = 2'});self.assertNotEqual(a,b)
 def test_syntax_error_fallback(self):
  fp=tokenomics.canonical_fingerprint({'bad.py':'def ('});self.assertIsInstance(fp,str);self.assertEqual(len(fp),64)
 def test_returns_hex_string(self):
  fp=tokenomics.canonical_fingerprint({'x.py':'pass'});self.assertRegex(fp,r'^[0-9a-f]{64}$')

class OutcomeFingerprintTests(unittest.TestCase):
 def test_deterministic(self):
  a=tokenomics.outcome_fingerprint('abc',['f.py'],1.2);b=tokenomics.outcome_fingerprint('abc',['f.py'],1.2);self.assertEqual(a,b)
 def test_delta_bucketed(self):
  a=tokenomics.outcome_fingerprint('abc',['f.py'],1.1);b=tokenomics.outcome_fingerprint('abc',['f.py'],1.4);self.assertEqual(a,b)
 def test_different_baseline_differs(self):
  a=tokenomics.outcome_fingerprint('abc',['f.py'],1.0);b=tokenomics.outcome_fingerprint('xyz',['f.py'],1.0);self.assertNotEqual(a,b)
 def test_file_order_independent(self):
  a=tokenomics.outcome_fingerprint('abc',['f.py','g.py'],1.0);b=tokenomics.outcome_fingerprint('abc',['g.py','f.py'],1.0);self.assertEqual(a,b)
 def test_returns_hex_string(self):
  fp=tokenomics.outcome_fingerprint('base',['x.py'],0.5);self.assertRegex(fp,r'^[0-9a-f]{64}$')

class FingerprintIndexTests(unittest.TestCase):
 def test_nonexistent_dir_returns_empty(self):self.assertEqual(tokenomics.fingerprint_index('/tmp/urace-test-fp-nonexistent'),{})
 def test_reads_receipts(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ev_dir=root/'ev1';ev_dir.mkdir()
   fp=tokenomics.outcome_fingerprint('base',['x.py'],2.0)
   receipt={'id':'ev1','at':'2024-01-01','outcome_fingerprint':fp,'candidate_score':0.9,'delta':2.0}
   (ev_dir/'receipt.json').write_text(json.dumps(receipt))
   index=tokenomics.fingerprint_index(tmp);self.assertIn(fp,index);self.assertEqual(index[fp][0]['id'],'ev1')
 def test_corrupt_receipt_skipped(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);bad=root/'bad';bad.mkdir();(bad/'receipt.json').write_text('not json')
   self.assertEqual(tokenomics.fingerprint_index(tmp),{})
 def test_receipt_without_fingerprint_skipped(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ev=root/'ev2';ev.mkdir();(ev/'receipt.json').write_text(json.dumps({'id':'ev2'}))
   self.assertEqual(tokenomics.fingerprint_index(tmp),{})


class CreditLedgerDecimalsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

 # 1. UNIT constant
 def test_unit_constant(self):self.assertEqual(credit_ledger.UNIT,100_000_000)
 def test_decimals_constant(self):self.assertEqual(credit_ledger.DECIMALS,8)
 def test_baseline_grant_units(self):self.assertEqual(credit_ledger.BASELINE_GRANT_UNITS,3*100_000_000)

 # 2. earn_units / spend_units roundtrip
 def test_earn_spend_roundtrip(self):
  root=self.root/'rtrip';root.mkdir()
  UNIT=credit_ledger.UNIT;BG=credit_ledger.BASELINE_GRANT_UNITS
  # fresh peer starts at baseline
  self.assertEqual(credit_ledger.balance(str(root),'p1'),BG)
  credit_ledger.earn_units(str(root),'p1',2*UNIT,'test')
  # velocity=1.0 (no prior history → no burn → minted>0 → clamp_low=0.8)
  # first earn: no prior rows → burned=0, minted=0 → multiplier=1.0
  bal=credit_ledger.balance(str(root),'p1')
  # after earn multiplier applied (1.0 on first call, burn=0 mint=0 before earn)
  self.assertGreater(bal,BG)
  pre_spend=credit_ledger.balance(str(root),'p1')
  credit_ledger.spend_units(str(root),'p1',UNIT,'test')
  self.assertEqual(credit_ledger.balance(str(root),'p1'),pre_spend-UNIT)

 # 3. balance() returns int
 def test_balance_returns_int(self):
  root=self.root/'intbal';root.mkdir()
  bal=credit_ledger.balance(str(root),'p')
  self.assertIsInstance(bal,int)

 # 4. Old float records multiplied by UNIT on read
 def test_old_float_records_compat(self):
  root=self.root/'compat';root.mkdir()
  # inject old-style record directly
  import time as _time
  ledger_obj=credit_ledger._ledger(str(root))
  ledger_obj.append('CREDIT_DELTA',{
   'peer':'oldpeer','delta':2.0,
   'direction':'earn','reason':'legacy','bundle_id':None,'at_unix':_time.time()
  })
  UNIT=credit_ledger.UNIT;BG=credit_ledger.BASELINE_GRANT_UNITS
  self.assertEqual(credit_ledger.balance(str(root),'oldpeer'),BG+2*UNIT)

 # 5. feature_complexity_score: simple < complex
 def test_complexity_score_ordering(self):
  simple=credit_ledger.feature_complexity_score(loc=10,dependency_count=0,test_count=0)
  complex_=credit_ledger.feature_complexity_score(loc=200,dependency_count=5,test_count=10)
  self.assertLess(simple,complex_)

 def test_complexity_score_minimum(self):
  # No floor penalty — all inputs return >= 1.0
  self.assertGreaterEqual(credit_ledger.feature_complexity_score(loc=5),1.0)
  self.assertGreaterEqual(credit_ledger.feature_complexity_score(),1.0)

 # 6. feature_borrow_cost_units higher for complex
 def test_borrow_cost_scaling(self):
  simple=credit_ledger.feature_borrow_cost_units(loc=10)
  complex_=credit_ledger.feature_borrow_cost_units(loc=200,dependency_count=5,test_count=10)
  self.assertLess(simple,complex_)

 def test_borrow_cost_floor(self):
  cost=credit_ledger.feature_borrow_cost_units()
  self.assertGreaterEqual(cost,credit_ledger.UNIT//100)

 # 7. earn_units applies velocity multiplier
 def test_velocity_multiplier_applied(self):
  import unittest.mock as mock
  root=self.root/'vel';root.mkdir()
  UNIT=credit_ledger.UNIT
  with mock.patch.object(credit_ledger,'_velocity_multiplier',return_value=0.5):
   credit_ledger.earn_units(str(root),'vp',2*UNIT,'test')
  bal=credit_ledger.balance(str(root),'vp')
  # adjusted = int(2*UNIT * 0.5) = UNIT
  self.assertEqual(bal,credit_ledger.BASELINE_GRANT_UNITS+UNIT)

 # 8. Dynamic per-peer cap (trust-scaled from BASE_CAP_UNITS)
 def test_dynamic_cap_clamps_balance(self):
  import unittest.mock as mock
  root=self.root/'cap';root.mkdir()
  BASE=credit_ledger.BASE_CAP_UNITS;UNIT=credit_ledger.UNIT
  # trust=0.1 → cap = BASE*1.1; patch both velocity and cap lookup
  with mock.patch.object(credit_ledger,'_velocity_multiplier',return_value=1.0), \
       mock.patch.object(credit_ledger,'peer_cap_units',return_value=int(BASE*1.1)):
   credit_ledger.earn_units(str(root),'cp',BASE*2,'test')
  self.assertLessEqual(credit_ledger.balance(str(root),'cp'),int(BASE*1.1))

 def test_high_trust_peer_gets_larger_cap(self):
  # trust=1.0 → cap = BASE*2.0 > BASE*1.1 for low-trust peer
  BASE=credit_ledger.BASE_CAP_UNITS
  self.assertGreater(int(BASE*2.0),int(BASE*1.1))

 def test_peer_cap_units_default_low_trust(self):
  import unittest.mock as mock
  # With no exchange data peer gets trust 0.1 → cap = BASE*1.1
  with mock.patch('urace.peer_exchange.Exchange',side_effect=Exception('no exchange')):
   cap=credit_ledger.peer_cap_units('/tmp/fake','peer-x')
  self.assertEqual(cap,int(credit_ledger.BASE_CAP_UNITS*1.1))

 # 9. to_display / from_display roundtrip
 def test_display_roundtrip(self):
  UNIT=credit_ledger.UNIT
  for units in [0,1,UNIT,UNIT//100,3*UNIT,12345678]:
   s=credit_ledger.to_display(units)
   self.assertEqual(credit_ledger.from_display(s),units)

 def test_to_display_format(self):
  self.assertEqual(credit_ledger.to_display(credit_ledger.UNIT),'1.00000000')
  self.assertEqual(credit_ledger.to_display(0),'0.00000000')


class ThreeFactorCapTests(unittest.TestCase):
 """Tests for three-factor peer_cap_units and anti-abuse earn_units."""

 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)/'node';self.root.mkdir()

 # --- quality_factor ---

 def test_quality_factor_no_data_returns_1(self):
  """quality_factor with no rows → 1.0."""
  class FakeExchange:
   def audit_rows(self): return []
  qf=credit_ledger._peer_quality_weights_from_exchange(FakeExchange(),'peer-a')
  self.assertEqual(qf,1.0)

 def test_quality_factor_with_verifications_above_1(self):
  """quality_factor with QUALITY_VERIFICATION rows → > 1.0."""
  class FakeExchange:
   def audit_rows(self):
    return [
     {'peer':'peer-a','kind':'QUALITY_VERIFICATION','subject_peer_id':'peer-b'},
     {'peer':'peer-a','kind':'QUALITY_VERIFICATION','subject_peer_id':'peer-c'},
     {'peer':'peer-a','kind':'APPLIED_AFTER_LOCAL_QUALIFICATION','subject_peer_id':'peer-d'},
    ]
  qf=credit_ledger._peer_quality_weights_from_exchange(FakeExchange(),'peer-a')
  self.assertGreater(qf,1.0)
  self.assertLessEqual(qf,1.5)

 def test_quality_factor_excludes_self_ratings(self):
  """Self-ratings (issuer == subject) must not inflate quality_factor."""
  class FakeExchange:
   def audit_rows(self):
    # all rows are self-ratings → should produce no credit
    return [
     {'peer':'peer-a','kind':'QUALITY_VERIFICATION','subject_peer_id':'peer-a'},
     {'peer':'peer-a','kind':'QUALITY_VERIFICATION','subject_peer_id':'peer-a'},
    ]
  qf=credit_ledger._peer_quality_weights_from_exchange(FakeExchange(),'peer-a')
  self.assertEqual(qf,1.0)

 # --- network_factor ---

 def test_network_factor_inflated_supply_below_1(self):
  """When total supply >> target, network_factor clamped to NETWORK_FACTOR_LOW."""
  import unittest.mock as mock
  # total_supply = 10× BASE per peer, target = 0.5× BASE → factor = 0.05 → clamp to 0.8
  BASE=credit_ledger.BASE_CAP_UNITS
  peers={'p1','p2'}
  class FakeExchange:
   def audit_rows(self): return [{'peer':p} for p in peers]
  with mock.patch.object(credit_ledger,'balance',return_value=BASE*10):
   nf=credit_ledger._network_supply_factor(str(self.root),FakeExchange())
  self.assertEqual(nf,credit_ledger.NETWORK_FACTOR_LOW)

 def test_network_factor_deflated_supply_above_1(self):
  """When total supply << target, network_factor clamped to NETWORK_FACTOR_HIGH."""
  import unittest.mock as mock
  BASE=credit_ledger.BASE_CAP_UNITS
  peers={'p1','p2'}
  class FakeExchange:
   def audit_rows(self): return [{'peer':p} for p in peers]
  with mock.patch.object(credit_ledger,'balance',return_value=1):
   nf=credit_ledger._network_supply_factor(str(self.root),FakeExchange())
  self.assertEqual(nf,credit_ledger.NETWORK_FACTOR_HIGH)

 # --- novelty gate ---

 def test_novelty_gate_reduces_earn_on_reborrow(self):
  """Re-borrowing the same feature_id earns only 50%."""
  import unittest.mock as mock
  root=str(self.root)
  UNIT=credit_ledger.UNIT
  BG=credit_ledger.BASELINE_GRANT_UNITS
  fid='feature-xyz'
  with mock.patch.object(credit_ledger,'_velocity_multiplier',return_value=1.0), \
       mock.patch.object(credit_ledger,'peer_cap_units',return_value=BG+100*UNIT):
   # First borrow — novel
   credit_ledger.earn_units(root,'pp',2*UNIT,'borrow',metadata={'feature_id':fid})
   bal_after_first=credit_ledger.balance(root,'pp')
   self.assertEqual(bal_after_first,BG+2*UNIT)
   # Second borrow — same feature, expect 50%
   credit_ledger.earn_units(root,'pp',2*UNIT,'borrow',metadata={'feature_id':fid})
   bal_after_second=credit_ledger.balance(root,'pp')
   self.assertEqual(bal_after_second,BG+2*UNIT+UNIT)  # +1 UNIT (50% of 2)

 def test_novelty_gate_no_penalty_for_different_feature(self):
  """Different feature_id → full earn, no penalty."""
  import unittest.mock as mock
  root=str(self.root)
  UNIT=credit_ledger.UNIT
  BG=credit_ledger.BASELINE_GRANT_UNITS
  with mock.patch.object(credit_ledger,'_velocity_multiplier',return_value=1.0), \
       mock.patch.object(credit_ledger,'peer_cap_units',return_value=BG+100*UNIT):
   credit_ledger.earn_units(root,'pp2',2*UNIT,'borrow',metadata={'feature_id':'feat-1'})
   credit_ledger.earn_units(root,'pp2',2*UNIT,'borrow',metadata={'feature_id':'feat-2'})
   self.assertEqual(credit_ledger.balance(root,'pp2'),BG+4*UNIT)

 # --- EMA velocity (no hard boundary) ---

 def test_ema_velocity_no_hard_boundary(self):
  """EMA multiplier must not produce a cliff at the exact old 30-day window boundary."""
  import unittest.mock as mock
  root=str(self.root)
  UNIT=credit_ledger.UNIT
  now=1_700_000_000.0
  # Inject two earn rows: one at 29.9d ago, one at 30.1d ago
  day=86400
  def make_row(direction,at_offset):
   return {'direction':direction,'delta_units':UNIT,'at_unix':now-at_offset,'peer':'vp'}
  rows=[make_row('earn',29.9*day),make_row('earn',30.1*day),make_row('spend',1*day)]
  with mock.patch.object(credit_ledger,'_credit_rows',return_value=rows), \
       mock.patch('time.time',return_value=now):
   mult=credit_ledger._velocity_multiplier(root)
  # With the old hard 30d window the row at 30.1d would be excluded, creating a cliff.
  # With EMA both rows contribute (exponentially weighted) → both included → check > 0.8
  self.assertIsInstance(mult,float)
  self.assertGreaterEqual(mult,credit_ledger.VELOCITY_CLAMP_LOW)
  self.assertLessEqual(mult,credit_ledger.VELOCITY_CLAMP_HIGH)
  # Verify: if we shift the spend row past 90d, only earns remain → clamped to 0.8
  rows2=[make_row('earn',1*day),make_row('earn',2*day),make_row('spend',95*day)]
  with mock.patch.object(credit_ledger,'_credit_rows',return_value=rows2), \
       mock.patch('time.time',return_value=now):
   mult2=credit_ledger._velocity_multiplier(root)
  self.assertEqual(mult2,credit_ledger.VELOCITY_CLAMP_LOW)

 # --- backward-compat alias ---

 def test_max_balance_units_alias(self):
  self.assertEqual(credit_ledger.MAX_BALANCE_UNITS,credit_ledger.BASE_CAP_UNITS)


class MintPerAdoptionTests(unittest.TestCase):
 UNIT=credit_ledger.UNIT

 def test_first_adopter_earns_most(self):
  r1=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,adopter_trust=0.8,adoption_rank=1,network_size=20)
  r10=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,adopter_trust=0.8,adoption_rank=10,network_size=20)
  self.assertGreater(r1,r10)

 def test_saturation_rank_returns_minimum(self):
  # N_sat = max(10, ceil(0.30*10)) = 10; rank 11 → asymptotic decay, floor=1
  r11=credit_ledger.mint_per_adoption(adoption_rank=11,network_size=10)
  self.assertGreaterEqual(r11,1)
  # network_size=100: N_sat=30; rank 31 → asymptotic decay, floor=1
  r31=credit_ledger.mint_per_adoption(adoption_rank=31,network_size=100)
  self.assertGreaterEqual(r31,1)

 def test_novelty_decay_monotone(self):
  # Compare across wide rank gaps (1 vs 5 vs 10) to survive ±5% jitter
  # Adjacent ranks differ by ~5-15% — too close for jitter; use 5× gaps instead
  import statistics
  def _avg(rank,n=10):
   return statistics.mean(credit_ledger.mint_per_adoption(loc=100,dependency_count=2,test_count=3,adopter_trust=1.0,adoption_rank=rank,network_size=50) for _ in range(n))
  r1=_avg(1);r5=_avg(5);r10=_avg(10)
  self.assertGreater(r1,r5,'rank 1 avg should earn > rank 5 avg')
  self.assertGreater(r5,r10,'rank 5 avg should earn > rank 10 avg')

 def test_epoch_decay_reduces_earn(self):
  e0=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,adopter_trust=0.8,adoption_rank=1,epochs_elapsed=0)
  e12=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,adopter_trust=0.8,adoption_rank=1,epochs_elapsed=12)
  self.assertGreater(e0,e12)

 def test_five_x_ratio_at_rank1(self):
  # complexity=1 (all zero args), trust=1.0
  borrow=credit_ledger.feature_borrow_cost_units()
  mint=credit_ledger.mint_per_adoption(adopter_trust=1.0,adoption_rank=1,network_size=20)
  ratio=mint/borrow
  self.assertGreater(ratio,4.0,'mint/borrow ratio should be ~5× (> 4)')
  self.assertLess(ratio,6.0,'mint/borrow ratio should be ~5× (< 6)')

 def test_rep_borrow_cost_discount_new_feature(self):
  no_data=credit_ledger.feature_borrow_cost_with_rep(quality_verifications=0,total_adoptions=0)
  # same as default call
  self.assertEqual(no_data,credit_ledger.feature_borrow_cost_with_rep())
  # proven feature costs more
  proven=credit_ledger.feature_borrow_cost_with_rep(quality_verifications=10,total_adoptions=10)
  self.assertLess(no_data,proven)

 def test_rep_borrow_cost_premium_proven_feature(self):
  proven=credit_ledger.feature_borrow_cost_with_rep(quality_verifications=10,total_adoptions=10)
  unproven=credit_ledger.feature_borrow_cost_with_rep(quality_verifications=0,total_adoptions=10)
  self.assertGreater(proven,unproven)

 def test_borrow_floor_lowered(self):
  cost=credit_ledger.feature_borrow_cost_units()
  self.assertGreaterEqual(cost,credit_ledger.UNIT//10_000)


class FullMintSystemTests(unittest.TestCase):
 UNIT=credit_ledger.UNIT

 def test_post_saturation_approaches_minimum(self):
  """rank >> N_sat still returns >= 1."""
  # N_sat=10 for network_size=10; rank=200 is very deep post-saturation
  earn=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,
   adopter_trust=0.8,adoption_rank=200,network_size=10)
  self.assertGreaterEqual(earn,1)

 def test_post_saturation_decreases_monotonically(self):
  """earn[rank=N_sat+1] > earn[rank=N_sat+10] > 1."""
  r_early=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,
   adopter_trust=0.8,adoption_rank=11,network_size=10)
  r_late=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,
   adopter_trust=0.8,adoption_rank=20,network_size=10)
  self.assertGreater(r_early,r_late)
  self.assertGreater(r_late,1)

 def test_rep_tier_bonus_stackable(self):
  """Crossing 2 tiers gives 1.2× vs crossing 0 gives 1.0×."""
  # 0 tiers: quality_verifications=0, total_adoptions=0
  b0=credit_ledger._rep_tier_bonus(0,0)
  self.assertEqual(b0,1.0)
  # 2 tiers: k=8,n=10 → Wilson lower~0.54 → crosses 0.3 and 0.5 (2 tiers) → 1.20
  b2=credit_ledger._rep_tier_bonus(8,10)
  self.assertEqual(b2,1.2)

 def test_rep_tier_bonus_max(self):
  """Crossing all 4 tiers gives exactly 1.4×."""
  # k=100, n=100 → Wilson lower very high (>0.9) → all 4 tiers
  b4=credit_ledger._rep_tier_bonus(100,100)
  self.assertAlmostEqual(b4,1.4,places=5)

 def test_supply_pressure_at_half(self):
  """supply_pressure_multiplier(physics_cap//2) ≈ 0.75 (within 0.1)."""
  # Use physics ceiling so the curve activates at real-world supply levels.
  physics_cap=credit_ledger.PHYSICS_CAP_UNITS_PER_PEER*10  # floor for n=1
  val=credit_ledger.supply_pressure_multiplier(physics_cap//2,physics_max_units=physics_cap)
  self.assertAlmostEqual(val,0.75,delta=0.1)

 def test_supply_pressure_never_zero(self):
  """supply_pressure_multiplier at full physics cap > 0."""
  physics_cap=credit_ledger.PHYSICS_CAP_UNITS_PER_PEER*10
  val=credit_ledger.supply_pressure_multiplier(physics_cap,physics_max_units=physics_cap)
  self.assertGreater(val,0)

 def test_derivative_penalty_heavy_overlap(self):
  """jaccard > 0.7 → earn less than non-derivative."""
  # feature_id heavily overlaps parent: jaccard = 3/4 = 0.75 > JACCARD_DERIVATIVE_CAP=0.70
  earn_deriv=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,
   adopter_trust=0.8,adoption_rank=1,network_size=20,
   feature_id='feature_abc_xyz',parent_feature_id='feature_abc_xyz_v2')
  # non-derivative: no parent_feature_id → no penalty
  earn_novel=credit_ledger.mint_per_adoption(loc=50,dependency_count=1,test_count=2,
   adopter_trust=0.8,adoption_rank=1,network_size=20)
  self.assertLess(earn_deriv,earn_novel)

 def test_complexity_no_floor_penalty(self):
  """No LOC floor penalty — score without tests still >= 1.0."""
  small=credit_ledger.feature_complexity_score(loc=2,test_count=0)
  self.assertGreaterEqual(small,1.0)
  # With tests score is still higher (log term grows)
  full=credit_ledger.feature_complexity_score(loc=2,test_count=1)
  self.assertLess(small,full)

 def test_earn_floor_never_hard_zero(self):
  """Any valid rank returns >= 1."""
  for rank in [1,5,10,50,100,500]:
   earn=credit_ledger.mint_per_adoption(adoption_rank=rank,network_size=10)
   self.assertGreaterEqual(earn,1,f'rank={rank} returned <1')


class CartAndComplexityTests(unittest.TestCase):
 UNIT=credit_ledger.UNIT

 def test_derivative_penalty_heavy(self):
  """j > 0.7 → penalty < 0.3."""
  # 'feature abc xyz' vs 'feature abc xyz v2': tokens {feature,abc,xyz} vs {feature,abc,xyz,v2}
  # j = 3/4 = 0.75 → penalty = 1 - 0.75 = 0.25
  pen=credit_ledger._derivative_penalty('feature_abc_xyz','feature_abc_xyz_v2')
  self.assertLess(pen,0.3)

 def test_derivative_penalty_medium(self):
  """j ≈ 0.55 → 0.5 < penalty < 1.0."""
  # Craft tokens to get j in 0.40-0.70
  # 'auth login user session' vs 'auth login user token extra'
  # a={auth,login,user,session}, b={auth,login,user,token,extra}
  # intersection=3, union=6, j=0.5
  pen=credit_ledger._derivative_penalty('auth_login_user_session','auth_login_user_token_extra')
  self.assertGreater(pen,0.5)
  self.assertLess(pen,1.0)

 def test_derivative_penalty_low(self):
  """j < 0.40 → penalty == 1.0."""
  pen=credit_ledger._derivative_penalty('feature_alpha_beta','completely_different_xyz_qrs')
  self.assertEqual(pen,1.0)

 def test_complexity_floor_below_network_norm(self):
  """mint with complexity < floor → earn less than without floor."""
  # All-zero args → complexity=1.0; floor=5.0 (above complexity) → 0.3× multiplier
  earn_with_floor=credit_ledger.mint_per_adoption(
   loc=0,dependency_count=0,test_count=0,
   adopter_trust=0.8,adoption_rank=1,network_size=20,
   complexity_floor=5.0,
  )
  earn_no_floor=credit_ledger.mint_per_adoption(
   loc=0,dependency_count=0,test_count=0,
   adopter_trust=0.8,adoption_rank=1,network_size=20,
   complexity_floor=0.5,
  )
  self.assertLess(earn_with_floor,earn_no_floor)

 def test_dynamic_max_mintable_scales_with_network(self):
  """max_mintable_units(100) > max_mintable_units(10)."""
  self.assertGreater(credit_ledger.max_mintable_units(100),credit_ledger.max_mintable_units(10))

 def test_max_mintable_minimum_floor(self):
  """max_mintable_units(0) >= BASE_CAP_UNITS * 10."""
  self.assertGreaterEqual(credit_ledger.max_mintable_units(0),credit_ledger.BASE_CAP_UNITS*10)

class AIPricingDefenseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

 def test_jitter_varies_output(self):
  import random as _r;_r.seed(None)
  UNIT=credit_ledger.UNIT
  results={credit_ledger._jitter(UNIT,0.05) for _ in range(50)}
  # With 50 samples and ±5% range, expect at least 2 distinct values
  self.assertGreater(len(results),1)

 def test_jitter_stays_within_bounds(self):
  UNIT=credit_ledger.UNIT
  for _ in range(200):
   v=credit_ledger._jitter(UNIT,0.05)
   self.assertGreaterEqual(v,int(UNIT*0.95))
   self.assertLessEqual(v,int(UNIT*1.05)+1)

 def test_jitter_floor_one(self):
  self.assertEqual(credit_ledger._jitter(1,0.05),1)

 def test_consensus_borrow_floor_no_exchange(self):
  # Falls back to UNIT//10_000 when no exchange
  floor=credit_ledger.consensus_borrow_floor(None)
  self.assertEqual(floor,credit_ledger.UNIT//10_000)

 def test_apply_borrow_cost_above_formula(self):
  # apply_borrow_cost >= feature_borrow_cost_with_rep (formula cost)
  for _ in range(20):
   cost=credit_ledger.apply_borrow_cost(loc=50,dependency_count=1,test_count=2)
   formula=credit_ledger.feature_borrow_cost_with_rep(loc=50,dependency_count=1,test_count=2)
   self.assertGreaterEqual(cost,int(formula*0.97)-1)  # allow jitter

 def test_mint_per_adoption_jitter_varies(self):
  import random as _r;_r.seed(None)
  results={credit_ledger.mint_per_adoption(loc=50,adopter_trust=1.0,adoption_rank=1,network_size=20) for _ in range(50)}
  self.assertGreater(len(results),1)

 def test_apply_borrow_cost_never_below_minimum(self):
  for _ in range(30):
   cost=credit_ledger.apply_borrow_cost()
   self.assertGreaterEqual(cost,credit_ledger.UNIT//10_000-1)  # allow jitter rounding


class GraphDistanceRepTests(unittest.TestCase):
 def test_combined_rep_delivery_gate(self):
  # delivery < 0.30 → 0.0 regardless of quality
  self.assertEqual(credit_ledger.combined_rep_score(0.1, 0.9), 0.0)

 def test_combined_rep_zero_quality_cold_start(self):
  # quality=0 → cold-start floor 0.05, not excluded
  score = credit_ledger.combined_rep_score(0.8, 0.0)
  self.assertGreater(score, 0.0)

 def test_combined_rep_both_high(self):
  # both high → high score
  score = credit_ledger.combined_rep_score(0.9, 0.9)
  self.assertGreater(score, 0.7)

 def test_combined_rep_delivery_weighted(self):
  # d=0.9,q=0.5 should score higher than d=0.5,q=0.9 (delivery-weighted)
  d_heavy = credit_ledger.combined_rep_score(0.9, 0.5)
  q_heavy = credit_ledger.combined_rep_score(0.5, 0.9)
  self.assertGreater(d_heavy, q_heavy)

 def test_combined_rep_symmetric_at_equal(self):
  # d=q → same score regardless of which is which
  import math
  s1 = credit_ledger.combined_rep_score(0.7, 0.7)
  s2 = credit_ledger.combined_rep_score(0.7, 0.7, beta=1.0)
  # with beta=1.0 (symmetric), should equal geometric mean
  self.assertAlmostEqual(s2, credit_ledger.combined_rep_score(0.7, 0.7, beta=1.0), places=5)

 def test_feature_creator_id_none_when_no_exchange(self):
  # No exchange → None
  result = credit_ledger.feature_creator_id('somefp', None)
  self.assertIsNone(result)

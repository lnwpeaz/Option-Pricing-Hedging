"""External conventions and genuine engines; no mocked financial numbers."""
from dataclasses import replace
import importlib
import json
import zipfile
import numpy as np
import pytest
from option_hedging.asian_contracts import AsianOptionSpec
from option_hedging.pricing.asian_reference import geometric_price
from option_hedging.validation.asian_reference import integrate_two_fixing
from option_hedging.validation.asian_quantlib import (external_checks,reference_price,
    validate_fixing_dates,fixing_dates,assess_reference)
from option_hedging.experiments.provenance import capture_snapshot

BASE='2026-10-24'
S=AsianOptionSpec(100,100,-.02,.2,'call',(73/365,1.))
SETTINGS={'quantlib_version':'1.44','precision_target':.0005}


@pytest.mark.parametrize('kind',['call','put'])
@pytest.mark.parametrize('times',[(1.,),(73/365,146/365,1.)])
def test_external_geometric_matches_independent_formula_and_restores_date(kind,times):
    ql=pytest.importorskip('QuantLib')
    previous=ql.Settings.instance().evaluationDate
    s=replace(S,kind=kind,fixing_times=times,averaging='geometric')
    r=reference_price(s,base_date=BASE,settings=SETTINGS)
    assert r.status=='available'
    assert r.price==pytest.approx(geometric_price(s),abs=2e-11)
    assert ql.Settings.instance().evaluationDate==previous


@pytest.fixture(scope='module')
def arithmetic_checks():
    pytest.importorskip('QuantLib')
    return external_checks(S,base_date=BASE,settings=SETTINGS)


def test_arithmetic_external_engines_match_two_dimensional_integral(arithmetic_checks):
    ref=integrate_two_fixing(S)
    choi=[r for r in arithmetic_checks if r['engine']=='choi']
    assert len(choi)==3 and all(r['status']=='completed' for r in choi)
    assert choi[-1]['price']==pytest.approx(ref.price,abs=3e-5)
    mc=[r for r in arithmetic_checks if r['engine']=='mc_control']
    assert len(mc)==4 and all(r['error_estimate']>0 for r in mc)
    result=assess_reference(S,arithmetic_checks,settings=SETTINGS)
    fd=[r for r in arithmetic_checks if r['engine']=='fd']
    expected=max(2*abs(choi[-1]['price']-choi[-2]['price']),
                 2*abs(fd[-1]['price']-fd[-2]['price']),abs(choi[-1]['price']-fd[-1]['price']))
    assert result.precision_radius==pytest.approx(expected)
    assert result.price==choi[-1]['price'] and result.precision_kind=='empirical_cross_method'
    assert result.status in ('available','low_precision')


def test_date_alignment_and_one_day_mismatch_rejected():
    ql=pytest.importorskip('QuantLib')
    dates=fixing_dates(S,BASE)
    validate_fixing_dates(S,BASE,dates)
    with pytest.raises(ValueError):validate_fixing_dates(S,BASE,[dates[0]+1,dates[1]])
    with pytest.raises(ValueError):fixing_dates(replace(S,fixing_times=(.1,.25,.5)),BASE)
    old=ql.Settings.instance().evaluationDate
    unsupported=reference_price(replace(S,fixing_times=(.1,.25,.5)),base_date=BASE,settings=SETTINGS)
    assert unsupported.status=='unavailable' and unsupported.price is None
    assert ql.Settings.instance().evaluationDate==old


def test_missing_optional_library_is_explicit_and_base_pricing_still_works(monkeypatch):
    original=importlib.import_module
    def without_quantlib(name,*args,**kwargs):
        if name=='QuantLib':raise ModuleNotFoundError('optional QuantLib unavailable')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(importlib,'import_module',without_quantlib)
    r=reference_price(S,base_date=BASE,settings=SETTINGS)
    assert r.status=='unavailable' and r.price is None and r.precision_radius is None
    assert geometric_price(S)>0


def test_research_snapshot_retains_optional_pin_and_requirements(tmp_path):
    ql=pytest.importorskip('QuantLib')
    capture_snapshot(tmp_path,config_bytes=b'[option]\n',entrypoint='option_hedging.experiments.asian_study')
    with zipfile.ZipFile(tmp_path/'source_snapshot.zip') as z:
        meta=json.loads(z.read('SNAPSHOT.json'))
        assert meta['runtime_versions']['QuantLib']==ql.__version__=='1.44'
        assert b'QuantLib==1.44' in z.read('requirements-research.txt')
        assert b'QuantLib==1.44' in z.read('runtime-requirements.txt')

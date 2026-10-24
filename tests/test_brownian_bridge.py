"""Catch bridge order, interpolation weights, covariance and mutation errors."""
import math
import numpy as np
import pytest
from option_hedging.simulation.brownian_bridge import brownian_from_normals


@pytest.mark.parametrize('construction',['increments','bridge'])
def test_transform_exact_covariance_and_terminal_coordinate(construction):
    t=np.array([.05,.2,.7,1.])
    f=brownian_from_normals(np.eye(4),t,construction=construction)
    np.testing.assert_allclose(f.T@f,np.minimum.outer(t,t),atol=2e-15)
    if construction=='bridge':np.testing.assert_allclose(f[:,-1],[1,0,0,0],atol=1e-15)


def test_irregular_grid_hand_values_and_nonmutation():
    z=np.array([[1.,-2.]])
    w=brownian_from_normals(z,(.25,1.))
    assert w[0]==pytest.approx([.5,.5-2*math.sqrt(.75)])
    wb=brownian_from_normals(z,(.25,1.),construction='bridge')
    assert wb[0]==pytest.approx([.25-2*math.sqrt(.1875),1.])
    np.testing.assert_array_equal(z,[[1.,-2.]])


@pytest.mark.parametrize('z',[[1,2],np.zeros((2,3)),[['1','2']],[[True,False]],[[1,float('nan')]],[[1,1j]]])
def test_invalid_normal_arrays_rejected(z):
    with pytest.raises((ValueError,TypeError)):brownian_from_normals(z,(.25,1.))


@pytest.mark.parametrize('construction',['increments','bridge'])
def test_repeated_ensembles_have_brownian_law(construction):
    t=np.array([.07,.2,.5,1.])
    means=[];covs=[]
    for seed in range(8):
        z=np.random.default_rng(seed+910).standard_normal((8192,4))
        w=brownian_from_normals(z,t,construction=construction)
        means.append(w.mean(axis=0));covs.append(np.cov(w,rowvar=False))
    assert np.max(np.abs(np.mean(means,axis=0)))<.015
    np.testing.assert_allclose(np.mean(covs,axis=0),np.minimum.outer(t,t),atol=.025,rtol=0)


def test_invalid_transform_and_times():
    with pytest.raises(ValueError):brownian_from_normals([[1.,2.]],(.5,1.),construction='other')
    with pytest.raises(ValueError):brownian_from_normals([[1.,2.]],(.5,.5))


def test_tiny_conditional_variance_is_preserved_or_explicitly_rejected():
    times=(5e-324,1e-323)
    try:transform=brownian_from_normals(np.eye(2),times,construction='bridge')
    except FloatingPointError:return
    want=[[math.sqrt(times[1])/2,math.sqrt(times[1])],
          [math.sqrt(times[0])*math.sqrt(.5),0.]]
    np.testing.assert_allclose(transform,want,rtol=2e-14,atol=0)

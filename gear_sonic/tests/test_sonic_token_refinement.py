import unittest
import numpy as np
import torch
from gear_sonic.scripts.refine_sonic_episode import TokenFitter

class LinearDecoder:
    device=torch.device('cpu')
    def __call__(self,x):return x[:29]

class LinearSession:
    def run(self,outputs,inputs):return [inputs['obs_dict'][:,:29].copy()]

class RefinementTest(unittest.TestCase):
    def test_fitted_token_decodes_to_target_without_changing_input(self):
        fitter=TokenFitter(LinearDecoder(),LinearSession(),iterations=5)
        obs=np.zeros(994,dtype='float32');slots=np.array([0,3,8,12,16,20,26,28])
        desired=np.linspace(-.2,.2,8,dtype='float32')
        scale=np.full(29,.5);default=np.full(29,.1)
        token=fitter(0,512,obs,desired,slots,default,scale)
        decoded=LinearSession().run(None,{'obs_dict':np.r_[token,obs[64:]][None]})[0][0]
        np.testing.assert_allclose((decoded*scale+default)[slots],desired,atol=2e-4)
        np.testing.assert_array_equal(obs,0.)
        self.assertLess(fitter.log[-1]['max_target_error_rad'],2e-4)
    def test_mismatching_gradient_model_is_rejected(self):
        class WrongSession:
            def run(self,outputs,inputs):return [np.ones((1,29),dtype='float32')]
        fitter=TokenFitter(LinearDecoder(),WrongSession())
        with self.assertRaisesRegex(RuntimeError,'parity'):
            fitter(0,0,np.zeros(994,dtype='float32'),np.zeros(8),np.arange(8),np.zeros(29),np.ones(29))

if __name__=='__main__':unittest.main()

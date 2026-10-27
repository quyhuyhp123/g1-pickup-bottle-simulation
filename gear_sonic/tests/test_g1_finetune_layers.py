import unittest
import torch
from torch import nn
from gear_sonic.scripts.finetune_gr00t_g1 import G1Linear,LoRALinear

class CategoryLinear(nn.Module):
    def __init__(self):
        super().__init__();self.W=nn.Parameter(torch.randn(3,4,5));self.b=nn.Parameter(torch.randn(3,5))
    def forward(self,x,c):return torch.bmm(x,self.W[c])+self.b[c,None,:]

class FineTuneLayersTest(unittest.TestCase):
    def test_g1_merge_preserves_other_embodiments(self):
        base=CategoryLinear().requires_grad_(False);original=base.W.detach().clone()
        wrapped=G1Linear(base,1);x=torch.randn(2,3,4);cat=torch.tensor([1,1])
        torch.testing.assert_close(wrapped(x,cat),base(x,cat))
        with torch.no_grad():wrapped.W.add_(.1);wrapped.b.sub_(.2)
        predicted=wrapped(x,cat).detach();merged=wrapped.merge()
        torch.testing.assert_close(predicted,merged(x,cat))
        torch.testing.assert_close(merged.W[[0,2]],original[[0,2]])
        with self.assertRaises(ValueError):wrapped(x,torch.tensor([0,1]))
    def test_lora_merge_preserves_updated_function(self):
        base=nn.Linear(4,7).requires_grad_(False);x=torch.randn(2,3,4)
        wrapped=LoRALinear(base,rank=2).eval()
        torch.testing.assert_close(wrapped(x),base(x))
        with torch.no_grad():wrapped.B.normal_(0,.1)
        result=wrapped(x).detach();merged=wrapped.merge()
        torch.testing.assert_close(result,merged(x),rtol=1e-5,atol=1e-6)

if __name__=='__main__':unittest.main()

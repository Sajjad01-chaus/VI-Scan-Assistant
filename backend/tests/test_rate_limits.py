import asyncio
import httpx
import pytest
from backend.app import providers
from backend.app.providers import ProviderError

@pytest.mark.parametrize('retry_after,seconds',[('3600',3600),('invalid',60)])
def test_rate_limit_cooldown_prevents_repeated_calls_and_does_not_block_other_models(monkeypatch,retry_after,seconds):
    providers._provider_cooldowns.clear();calls=[]
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,**kwargs):
            calls.append((url,kwargs['json']['model']))
            return httpx.Response(429,headers={'retry-after':retry_after}) if kwargs['json']['model']=='limited' else httpx.Response(200,json={'ok':True})
    monkeypatch.setattr(providers.httpx,'AsyncClient',Client)
    monkeypatch.setattr(providers.time,'monotonic',lambda:100.)
    async def run():
        for _ in range(2):
            with pytest.raises(ProviderError) as failure:
                await providers.post('https://test.invalid/speech',{},json={'model':'limited'})
            assert failure.value.code=='provider_rate_limit'
        assert providers._provider_cooldowns[('https://test.invalid/speech','limited')]==100+seconds
        result=await providers.post('https://test.invalid/speech',{},json={'model':'other'})
        assert result.status_code==200
    try:
        asyncio.run(run());assert len(calls)==2
    finally:providers._provider_cooldowns.clear()

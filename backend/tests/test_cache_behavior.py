from backend.tests.test_workflows import client,new,command
import backend.app.main as main


def test_app_and_config_expose_running_build_with_cache_policy(client):
    config=client.get('/api/config')
    assert config.headers['cache-control']=='no-store'
    assert config.json()['build_id']==main.BUILD_ID==config.headers['x-app-build']
    index=client.get('/')
    assert index.headers['cache-control']=='no-cache, must-revalidate'
    assert index.headers['x-app-build']==main.BUILD_ID


def test_new_utterance_is_new_turn_but_refresh_restores_original_answers(client):
    session=new(client)
    first=command(client,session,'Thank you.','first')
    second=command(client,first['session'],'Thank you.','second')
    assert first['turn_id']!=second['turn_id'] and not second.get('replayed')
    retry=command(client,second['session'],'Thank you.','first')
    assert retry['turn_id']==first['turn_id'] and retry['replayed']
    history=client.get('/api/sessions/'+session['id']+'/history')
    assert history.headers['cache-control']=='no-store'
    assert [m['result']['turn_id'] for m in history.json()['messages'] if m['role']=='assistant']==[first['turn_id'],second['turn_id']]

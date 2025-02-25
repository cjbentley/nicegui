import asyncio
from pathlib import Path

import httpx

from nicegui import Client, app, background_tasks, ui

from .screen import PORT, Screen


def test_browser_data_is_stored_in_the_browser(screen: Screen):
    @ui.page('/')
    def page():
        app.storage.browser['count'] = app.storage.browser.get('count', 0) + 1
        ui.label().bind_text_from(app.storage.browser, 'count')

    @app.get('/count')
    def count():
        return 'count = ' + str(app.storage.browser['count'])

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    screen.should_contain('1')
    screen.open('/')
    screen.should_contain('2')
    screen.open('/')
    screen.should_contain('3')
    screen.open('/count')
    screen.should_contain('count = 3')  # also works with FastAPI endpoints


def test_browser_storage_supports_asyncio(screen: Screen):
    @ui.page('/')
    async def page():
        app.storage.browser['count'] = app.storage.browser.get('count', 0) + 1
        await asyncio.sleep(0.5)
        ui.label(app.storage.browser['count'])

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    screen.switch_to(1)
    screen.open('/')
    screen.should_contain('2')
    screen.switch_to(0)
    screen.open('/')
    screen.should_contain('3')


def test_browser_storage_modifications_after_page_load_are_forbidden(screen: Screen):
    @ui.page('/')
    async def page(client: Client):
        await client.connected()
        try:
            app.storage.browser['test'] = 'data'
        except TypeError as e:
            ui.label(str(e))

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    screen.should_contain('response to the browser has already been built')


def test_user_storage_modifications(screen: Screen):
    @ui.page('/')
    async def page(client: Client, delayed: bool = False):
        if delayed:
            await client.connected()
        app.storage.user['count'] = app.storage.user.get('count', 0) + 1
        ui.label().bind_text_from(app.storage.user, 'count')

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    screen.should_contain('1')
    screen.open('/?delayed=True')
    screen.should_contain('2')
    screen.open('/')
    screen.should_contain('3')


async def test_access_user_storage_from_fastapi(screen: Screen):
    @app.get('/api')
    def api():
        app.storage.user['msg'] = 'yes'
        return 'OK'

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(f'http://localhost:{PORT}/api')
        assert response.status_code == 200
        assert response.text == '"OK"'
        await asyncio.sleep(0.5)  # wait for storage to be written
        assert next(Path('.nicegui').glob('storage_user_*.json')).read_text() == '{"msg": "yes"}'


def test_access_user_storage_on_interaction(screen: Screen):
    @ui.page('/')
    async def page():
        if 'test_switch' not in app.storage.user:
            app.storage.user['test_switch'] = False
        ui.switch('switch').bind_value(app.storage.user, 'test_switch')

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    screen.click('switch')
    screen.wait(0.5)
    assert '{"test_switch": true}' in next(Path('.nicegui').glob('storage_user_*.json')).read_text()


def test_access_user_storage_from_button_click_handler(screen: Screen):
    @ui.page('/')
    async def page():
        ui.button('test', on_click=app.storage.user.update(inner_function='works'))

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    screen.click('test')
    screen.wait(1)
    assert '{"inner_function": "works"}' in next(Path('.nicegui').glob('storage_user_*.json')).read_text()


async def test_access_user_storage_from_background_task(screen: Screen):
    @ui.page('/')
    def page():
        async def subtask():
            await asyncio.sleep(0.1)
            app.storage.user['subtask'] = 'works'
        background_tasks.create(subtask())

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    assert '{"subtask": "works"}' in next(Path('.nicegui').glob('storage_user_*.json')).read_text()


def test_user_and_general_storage_is_persisted(screen: Screen):
    @ui.page('/')
    def page():
        app.storage.user['count'] = app.storage.user.get('count', 0) + 1
        app.storage.general['count'] = app.storage.general.get('count', 0) + 1
        ui.label(f'user: {app.storage.user["count"]}')
        ui.label(f'general: {app.storage.general["count"]}')

    screen.ui_run_kwargs['storage_secret'] = 'just a test'
    screen.open('/')
    screen.open('/')
    screen.open('/')
    screen.should_contain('user: 3')
    screen.should_contain('general: 3')
    screen.selenium.delete_all_cookies()
    screen.open('/')
    screen.should_contain('user: 1')
    screen.should_contain('general: 4')

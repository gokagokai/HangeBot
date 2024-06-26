from urllib.parse import urljoin
import requests


class QueueObj:
    def __init__(self, event_loop, ctx, args):
        self.event_loop = event_loop
        self.ctx = ctx
        self.args = args


class WebUi:
    class WebuiException(Exception):
        pass

    def __init__(self, ip):
        self._base_url = ip

    def txt_to_img(self, queue_obj):
        endpoint = urljoin(self._base_url, '/sdapi/v1/txt2img')
        payload = queue_obj.args
        response = requests.post(url=endpoint, json=payload)
        r = response.json()
        return r, response.status_code
    
    def switch_model(self, queue_obj):
        endpoint = urljoin(self._base_url, '/sdapi/v1/options')
        payload = queue_obj.args
        response = requests.post(url=endpoint, json=payload)
        r = response.json()
        return r, response.status_code

    def get_progress(self):
        endpoint = urljoin(self._base_url, '/sdapi/v1/progress?skip_current_image=false')
        try:
            response = requests.get(endpoint)
            r = response.json()
            return r, response.status_code
        except requests.RequestException:
            return None, 500
        
    def get_png_info(self, base64_string):
        endpoint = urljoin(self._base_url, '/sdapi/v1/png-info')
        
        payload = {
            "image": base64_string
        }
        
        response = requests.post(url=endpoint, json=payload)
        r = response.json()
        return r, response.status_code
    
    def heartbeat(self):
        endpoint = urljoin(self._base_url, '/user/')
        try:
            r = requests.get(endpoint, timeout=10)
            return r.status_code == 200
        except:
            return False

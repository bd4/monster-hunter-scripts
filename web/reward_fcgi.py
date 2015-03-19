from flup.server.fcgi import WSGIServer

import reward_webapp

if __name__ == '__main__':
    WSGIServer(reward_webapp.application).run()

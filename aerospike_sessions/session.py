import aerospike

try:
    from django.utils.encoding import force_unicode
except ImportError:  # Python 3.*
    from django.utils.encoding import force_text as force_unicode
from django.contrib.sessions.backends.base import SessionBase, CreateError
from aerospike_sessions import settings




config = {
    "hosts": [
        ( settings.SESSION_AEROSPIKE_HOST, settings.SESSION_AEROSPIKE_PORT)
    ],
    "policies": settings.SESSION_AEROSPIKE_POLICY
}

aerospike_client = aerospike.client(config).connect(settings.SESSION_AEROSPIKE_USER_NAME, settings.SESSION_AEROSPIKE_PASSWORD)

class SessionStore(SessionBase):
    """
    Implements Aerospike database session store.
    """
    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key)

    def load(self):
        try:
            key, meta, session_data = aerospike_client.get(
                self.get_aerospike_tuple(self._get_or_create_session_key())
            )
            return self.decode(force_unicode(session_data.get('session_key','')))
        except:
            self._session_key = None
            return {}

    def exists(self, session_key):
        try:
            (key, meta) = aerospike_client.exists(self.get_aerospike_tuple(session_key))
            return meta != None
        except:
            return False

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()

            try:
                self.save(must_create=True)
            except CreateError:
                # Key wasn't unique. Try again.
                continue
            self.modified = True
            return

    def save(self, must_create=False):
        if self.session_key is None:
            return self.create()
        key, meta = aerospike_client.exists(self.get_aerospike_tuple(self._get_or_create_session_key()))
        if must_create and meta != None:
            raise CreateError
        data = {'session_key' : self.encode(self._get_session(no_load=must_create))}
        ttl = self.get_expiry_age() or  settings.SESSION_AEROSPIKE_EXPIRY
        aerospike_client.put(key, data, meta = {'ttl': ttl})

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        try:
            aerospike_client.remove(self.get_aerospike_tuple(session_key))
        except:
            pass

    def get_aerospike_tuple(self, session_key):
        """Return the real key name in redis storage
        @return string
        """
        namespace = settings.SESSION_AEROSPIKE_NAMESPACE
        set = settings.SESSION_AEROSPIKE_SET
        return ((namespace, set, session_key))
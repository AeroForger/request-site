// Public endpoint only. Email provider credentials stay on the server.
export const requestApiUrl = location.hostname.endsWith('.github.io') ?
    'https://request-site-tan.vercel.app/api/requests' :
    '/api/requests';

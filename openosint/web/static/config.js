// OpenOSINT runtime config — override before this script loads:
//   <script>window.OPENOSINT_CONFIG = { proxyBaseUrl: 'https://api.openosint.tech' };</script>
// In production, serve a rewritten version of this file via CDN/Docker env injection.
window.OPENOSINT_CONFIG = Object.assign(
  {
    proxyBaseUrl: '',   // '' = same-origin; set to full URL for cross-origin proxy
  },
  window.OPENOSINT_CONFIG || {}
);

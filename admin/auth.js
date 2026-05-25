// Wspólny moduł auth dla stron /admin/*.
// Wymaga załadowanego globalnego `supabase` z https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2

const SUPABASE_URL = 'https://iarvbkkbwddjljgvtyjp.supabase.co';
const HOME_PATH = '../';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlhcnZia2tid2RkamxqZ3Z0eWpwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg2OTc5MjcsImV4cCI6MjA5NDI3MzkyN30.kP9qRAqGn3_8LwIsrAlpQnK4-dvaz25vM8jAuweAOA4';

console.log('[auth.js] Initializing, window.supabase available?', !!window.supabase);

if (!window.supabase) {
  console.error('[auth.js] ERROR: window.supabase not available! CDN might have failed to load.');
  // Czekaj na Supabase
  setTimeout(() => {
    if (!window.supabase) {
      console.error('[auth.js] FATAL: Supabase still not loaded after 2s');
    }
  }, 2000);
}

let supa;
try {
  supa = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  });
  console.log('[auth.js] Supabase client created');
} catch (e) {
  console.error('[auth.js] Error creating Supabase client:', e);
}

window.GrandsAuth = {
  supa,
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  _authCallback: null,
  _logoutInProgress: false,

  async getAccessToken() {
    const { data: { session } } = await supa.auth.getSession();
    return session?.access_token || null;
  },

  async requireAdmin({ gateEl, appEl, onSuccess }) {
    let callbackFired = false;

    const check = async () => {
      const { data: { session } } = await supa.auth.getSession();
      if (!session) { renderLogin(gateEl, appEl); return null; }

      const { data: row, error } = await supa
        .from('admin_users').select('user_id').eq('user_id', session.user.id).maybeSingle();
      if (error || !row) { renderNoAccess(gateEl, appEl, session.user.email); return null; }

      gateEl.style.display = 'none';
      appEl.hidden = false;
      appEl.style.display = '';

      // Fire success callback only once - on successful access
      if (!callbackFired && onSuccess) {
        callbackFired = true;
        console.log('[auth.js] Admin access confirmed, firing onSuccess callback');
        // Schedule callback async to ensure DOM is ready
        setTimeout(onSuccess, 0);
      }

      return session.user;
    };

    // Perform initial check
    console.log('[auth.js] Running initial session check...');
    const user = await check();

    // Listen for session changes (new logins, logouts, token refresh)
    const { data: { subscription } } = supa.auth.onAuthStateChange((event, session) => {
      console.log('[auth.js] Auth state changed:', event, !!session);
      setTimeout(() => {
        check().catch(error => console.error('[auth.js] Auth state check failed:', error));
      }, 0);
    });

    return user;
  },

  async logout() {
    if (this._logoutInProgress) return;
    this._logoutInProgress = true;
    console.log('[auth.js] Logout started...');
    try {
      if (!supa) {
        console.error('[auth.js] ERROR: Supabase client not initialized');
        window.location.replace(HOME_PATH);
        return;
      }

      // Do not let a network/auth callback stall block the redirect.
      const signOutResult = await Promise.race([
        supa.auth.signOut().then(result => ({ ...result, timedOut: false })),
        new Promise(resolve => setTimeout(() => resolve({ error: null, timedOut: true }), 1500))
      ]);

      if (signOutResult.timedOut) {
        console.warn('[auth.js] Logout signOut timed out, continuing with local cleanup');
      } else if (signOutResult.error) {
        const { error } = signOutResult;
        console.error('[auth.js] Logout error:', error);
      } else {
        console.log('[auth.js] Logout successful, session cleared from Supabase');
      }

      // Also clear localStorage manually to ensure clean state
      try {
        const storageKeys = Object.keys(localStorage);
        storageKeys.forEach(key => {
          if (key.includes('supabase') || key.includes('auth')) {
            localStorage.removeItem(key);
            console.log('[auth.js] Cleared localStorage key:', key);
          }
        });
      } catch (e) {
        console.warn('[auth.js] Could not clear localStorage:', e);
      }

    } catch (e) {
      console.error('[auth.js] Fatal logout error:', e);
    } finally {
      console.log('[auth.js] Redirecting to home page...');
      window.location.replace(HOME_PATH);
    }
  }
};

function renderLogin(gateEl, appEl) {
  appEl.hidden = true;
  appEl.style.display = 'none';
  gateEl.style.display = 'flex';
  gateEl.innerHTML = `
    <div class="auth-card">
      <h1>Panel administracyjny</h1>
      <p class="muted">Zaloguj się aby zobaczyć dane.</p>
      <form id="login-form">
        <input type="text" id="login-username" value="admin" required autocomplete="username">
        <input type="password" id="login-password" placeholder="hasło" required autocomplete="current-password">
        <button type="submit" id="login-btn">Zaloguj</button>
      </form>
      <div id="login-msg" class="msg"></div>
    </div>`;
  gateEl.querySelector('#login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = gateEl.querySelector('#login-username').value.trim();
    const password = gateEl.querySelector('#login-password').value;
    const btn = gateEl.querySelector('#login-btn');
    const msg = gateEl.querySelector('#login-msg');

    msg.textContent = 'Logowanie…';
    btn.disabled = true;

    // Convert username to email by appending @grands.local
    const email = username.includes('@') ? username : `${username}@grands.local`;
    console.log('[auth.js] Login attempt:', email);

    const { error } = await supa.auth.signInWithPassword({ email, password });
    if (error) {
      console.error('[auth.js] Login error:', error);
      msg.textContent = `Błąd: ${error.message}`;
      btn.disabled = false;
    } else {
      console.log('[auth.js] Login successful, waiting for session update…');
      // Session update will trigger onAuthStateChange and requireAdmin callback
    }
  });
}

function renderNoAccess(gateEl, appEl, email) {
  appEl.hidden = true;
  appEl.style.display = 'none';
  gateEl.style.display = 'flex';
  gateEl.innerHTML = `
    <div class="auth-card">
      <h1>Brak uprawnień</h1>
      <p class="muted">Konto <strong>${email}</strong> nie ma uprawnień administratora.</p>
      <button id="logout-btn">Wyloguj</button>
    </div>`;
  gateEl.querySelector('#logout-btn').addEventListener('click', () => window.GrandsAuth.logout());
}

// Wspólny moduł auth dla stron /admin/*.
// Wymaga załadowanego globalnego `supabase` z https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2

const SUPABASE_URL = 'https://iarvbkkbwddjljgvtyjp.supabase.co';
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

  async getAccessToken() {
    const { data: { session } } = await supa.auth.getSession();
    return session?.access_token || null;
  },

  async requireAdmin({ gateEl, appEl }) {
    const check = async () => {
      const { data: { session } } = await supa.auth.getSession();
      if (!session) { renderLogin(gateEl, appEl); return null; }

      const { data: row, error } = await supa
        .from('admin_users').select('user_id').eq('user_id', session.user.id).maybeSingle();
      if (error || !row) { renderNoAccess(gateEl, appEl, session.user.email); return null; }

      gateEl.style.display = 'none';
      appEl.hidden = false;
      appEl.style.display = '';
      return session.user;
    };

    // pierwsze sprawdzenie
    const user = await check();

    // nasłuchiwanie zmian sesji (np. po zalogowaniu)
    supa.auth.onAuthStateChange(async () => {
      await check();
    });

    return user;
  },

  async logout() {
    console.log('[auth.js] Logout started...');
    // Redirect immediately - signOut happens in background
    location.href = '/';

    // Perform signOut asynchronously without waiting
    try {
      if (!supa) {
        console.error('[auth.js] ERROR: Supabase client not initialized');
        return;
      }
      const { error } = await supa.auth.signOut();
      if (error) {
        console.error('[auth.js] Logout error:', error);
      } else {
        console.log('[auth.js] Logout successful');
      }
    } catch (e) {
      console.error('[auth.js] Fatal logout error:', e);
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
        <button type="submit">Zaloguj</button>
      </form>
      <div id="login-msg" class="msg"></div>
    </div>`;
  gateEl.querySelector('#login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = gateEl.querySelector('#login-username').value.trim();
    const password = gateEl.querySelector('#login-password').value;
    const msg = gateEl.querySelector('#login-msg');
    msg.textContent = 'Logowanie…';
    // Convert username to email by appending @grands.local
    const email = username.includes('@') ? username : `${username}@grands.local`;
    const { error } = await supa.auth.signInWithPassword({ email, password });
    if (error) {
      msg.textContent = `Błąd: ${error.message}`;
    }
    // bez error — requireAdmin() się wywoła automatycznie po aktualizacji sesji
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

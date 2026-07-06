# Phase 9 — SaaS Dashboard & User Features

## Goal
Build the user-facing SaaS layer: dashboard, scan history, story progress, favorites. This transforms Wadjet from "use and forget" to "use and return." Depends on Phase 3 (DB + Auth) and Phase 8 (Stories).

## New Features
- User dashboard page (`/dashboard`)
- Scan history with thumbnail + results
- Story progress overview
- Favorites (landmarks, glyphs)
- Profile settings (name, language, password)
- "Save to history" integration in existing features
- Tier indicators (Free tier limits display)

## Files Created
- `app/templates/dashboard.html` — main dashboard page
- `app/templates/partials/dashboard_stats.html` — stats cards
- `app/templates/partials/dashboard_history.html` — scan history list
- `app/templates/partials/dashboard_progress.html` — story progress
- `app/templates/partials/dashboard_favorites.html` — saved items
- `app/templates/settings.html` — user settings page
- `app/templates/partials/auth_modal.html` — login/signup modal

## Files Modified
- `app/api/pages.py` — add /dashboard, /settings routes
- `app/api/scan.py` — save scan to history (if logged in)
- `app/api/user.py` — dashboard data endpoints
- `app/templates/partials/nav.html` — add dashboard link + user menu
- `app/templates/base.html` — include auth modal
- `app/templates/explore.html` — add "favorite" heart button
- `app/templates/stories.html` — show progress per story

## Implementation Steps

### Step 1: Dashboard page design
```
┌─────────────────────────────────────────────┐
│  Welcome back, Nour 👋                       │
│                                              │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │  12  │ │  3   │ │  45  │ │  2   │       │
│  │Scans │ │Stories│ │Glyphs│ │Favs  │       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│                                              │
│  Recent Scans                    View All →  │
│  ┌──────┐ ┌──────┐ ┌──────┐                │
│  │ img  │ │ img  │ │ img  │                │
│  │3 glyp│ │1 glyp│ │5 glyp│                │
│  │ 85%  │ │ 92%  │ │ 67%  │                │
│  └──────┘ └──────┘ └──────┘                │
│                                              │
│  Story Progress                              │
│  ▓▓▓▓▓▓▓▓░░ Osiris Myth (80%)              │
│  ▓▓▓░░░░░░░ Journey of Ra (30%)             │
│  ░░░░░░░░░░ Creation from Nun (0%)          │
│                                              │
│  Favorite Landmarks              View All →  │
│  🏛️ Karnak Temple · 🏛️ Abu Simbel          │
└─────────────────────────────────────────────┘
```

### Step 2: Auth modal (Alpine.js)
```html
<!-- partials/auth_modal.html -->
<div x-data="authModal()" x-show="open" x-cloak
     class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
    <div class="bg-surface border border-border rounded-2xl p-8 w-full max-w-md shadow-2xl">
        <!-- Tab switch: Sign In / Sign Up -->
        <div class="flex gap-4 mb-6">
            <button @click="mode = 'login'" :class="mode === 'login' ? 'text-gold border-b-2 border-gold' : 'text-text-muted'" class="pb-2 font-medium">
                {{ t('nav.sign_in') }}
            </button>
            <button @click="mode = 'register'" :class="mode === 'register' ? 'text-gold border-b-2 border-gold' : 'text-text-muted'" class="pb-2 font-medium">
                {{ t('nav.sign_up') }}
            </button>
        </div>

        <!-- Login Form -->
        <form x-show="mode === 'login'" @submit.prevent="login()">
            <label for="login-email" class="text-sm text-text-muted">Email</label>
            <input id="login-email" type="email" x-model="email" required
                   class="w-full mt-1 mb-4 px-4 py-3 bg-night border border-border rounded-lg text-text">
            <label for="login-password" class="text-sm text-text-muted">Password</label>
            <input id="login-password" type="password" x-model="password" required
                   class="w-full mt-1 mb-6 px-4 py-3 bg-night border border-border rounded-lg text-text">
            <button type="submit" class="btn-gold w-full" :disabled="loading">
                <span x-show="!loading">{{ t('nav.sign_in') }}</span>
                <span x-show="loading" class="animate-spin">⟳</span>
            </button>
        </form>

        <!-- Register Form (similar) -->
        ...

        <p x-show="error" class="mt-4 text-error text-sm text-center" x-text="error"></p>
    </div>
</div>
```

### Step 3: Nav user menu
When logged in, replace "Sign In" with user avatar dropdown:
```html
<!-- Logged in state -->
<div x-show="$store.auth.user" class="relative" x-data="{ userMenu: false }">
    <button @click="userMenu = !userMenu" class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-alt">
        <div class="w-8 h-8 rounded-full bg-gold/20 flex items-center justify-center text-gold text-sm font-bold"
             x-text="$store.auth.user?.display_name?.[0] || '𓂀'"></div>
    </button>
    <div x-show="userMenu" @click.away="userMenu = false"
         class="absolute right-0 mt-2 w-48 bg-surface border border-border rounded-lg shadow-xl py-2">
        <a href="/dashboard" class="block px-4 py-2 text-sm hover:bg-surface-alt">Dashboard</a>
        <a href="/settings" class="block px-4 py-2 text-sm hover:bg-surface-alt">Settings</a>
        <hr class="border-border my-1">
        <button @click="$store.auth.logout()" class="block w-full text-left px-4 py-2 text-sm text-error hover:bg-surface-alt">Sign Out</button>
    </div>
</div>
```

### Step 4: Save scans to history
In `scan.py`, after successful scan:
```python
# If user is logged in, save to history
user = await get_optional_user(request, db)
if user:
    await crud.create_scan_history(db, user.id, results_json, confidence_avg, glyph_count)
```

### Step 5: Favorite button on explore cards
```html
<button @click="toggleFavorite('landmark', '{{ site.id }}')"
        class="absolute top-3 right-3 p-2 rounded-full bg-night/60 backdrop-blur"
        :class="isFavorite('landmark', '{{ site.id }}') ? 'text-gold' : 'text-text-muted'">
    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
    </svg>
</button>
```

### Step 6: Free tier limits
Display limits for free users (without blocking — soft limits for beta):
```python
FREE_LIMITS = {
    "scans_per_day": 10,
    "chat_messages_per_day": 20,
    "stories_accessible": 3,  # First 3 stories free
}
```

Show as a banner when approaching limits:
```html
<div x-show="scanCount >= 8" class="bg-gold/10 border border-gold/30 rounded-lg p-3 text-sm text-gold">
    You've used 8 of 10 free scans today. <a href="/pricing" class="underline">Upgrade for unlimited access</a>
</div>
```

## Testing Checklist
- [ ] Sign up → account created, redirected to dashboard
- [ ] Login → JWT stored, nav shows user menu
- [ ] Dashboard loads with stats cards (scans, stories, glyphs, favorites)
- [ ] Recent scans section shows last 6 scans with thumbnails
- [ ] Story progress bars show correct percentages
- [ ] Favorites section shows saved landmarks/glyphs
- [ ] Click scan history item → shows full results
- [ ] Perform a scan while logged in → appears in history
- [ ] Heart button on explore → adds to favorites
- [ ] Heart button again → removes from favorites
- [ ] Settings page: change name, language, password
- [ ] Sign out → JWT cleared, nav shows "Sign In" again
- [ ] Guest user → all features work, "Sign in to save" prompts
- [ ] Free tier limit banner appears near limit
- [ ] Dashboard is responsive on mobile
- [ ] Dashboard works in Arabic (RTL)

## Git Commit
```
[Phase 9] SaaS dashboard — user dashboard, scan history, story progress, favorites, auth UI
```

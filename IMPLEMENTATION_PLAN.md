# Implementation Plan: Integration Issues

This document provides a detailed plan to address all integration issues identified in `INTEGRATION_ANALYSIS.md`.

---

## 🎯 Plan Overview

**Total Issues**: 8
- **Critical**: 1 (WebSocket message mismatch)
- **High Priority**: 1 (Token refresh)
- **Medium Priority**: 3 (PATCH job, Apps list, Job purge UI)
- **Low Priority**: 3 (Message management, Direct app viewing)

**Estimated Total Effort**: ~12-16 hours

---

## 🔴 Phase 1: Critical Fixes (Must Do First)

### Issue #1: Fix WebSocket Message Type Mismatch
**Priority**: 🔴 **CRITICAL**  
**Effort**: 2-3 hours  
**Impact**: Breaks real-time updates, causes unnecessary API polling

#### Problem
Server sends: `jobStatus`, `agentDialogue`, `stageUpdate`, `prdReady`  
Frontend expects: `status`, `step`, `chat`, `app`, `error`

#### Solution Options

**Option A: Update Server to Match Documentation (Recommended)**
- Aligns with `backend_doc.txt` specification
- More semantic naming (`status` vs `jobStatus`)
- Requires server changes only

**Option B: Update Frontend to Match Server**
- Less semantic naming
- Requires frontend changes only
- Doesn't match documentation

**Decision**: Choose Option A - Update server to match documentation

#### Implementation Steps

1. **Update `server/jobs/services.py`**:
   - Change `'kind': 'jobStatus'` → `'kind': 'status'` (line 58)
   - Change `'kind': 'agentDialogue'` → `'kind': 'step'` (line 87)
   - Change `'kind': 'stageUpdate'` → `'kind': 'chat'` (line 290)
   - Change `'kind': 'prdReady'` → `'kind': 'app'` (line 117)
   - Ensure payload fields match frontend expectations:
     - `status` message: `{ kind: 'status', jobId, status, message, timestamp }`
     - `step` message: `{ kind: 'step', jobId, agent, message, order, timestamp }`
     - `chat` message: `{ kind: 'chat', jobId, role, sender, content, metadata, timestamp }`
     - `app` message: `{ kind: 'app', jobId, spec, timestamp }` (include `prdMarkdown` if needed)

2. **Verify Frontend Compatibility**:
   - Check `client/src/pages/LiveBuild.tsx` handles all message types correctly
   - Ensure `client/src/hooks/useWebSocket.ts` type definitions match
   - Test that `refetch()` calls can be removed (use real-time data instead)

3. **Update Tests** (if any):
   - Update any WebSocket message tests to use new message kinds

4. **Testing Checklist**:
   - [ ] Create a new job
   - [ ] Verify `chat` messages appear in real-time
   - [ ] Verify `status` updates appear in real-time
   - [ ] Verify `step` messages appear in real-time
   - [ ] Verify `app` message appears when job completes
   - [ ] Verify no unnecessary `refetch()` calls (check network tab)
   - [ ] Test WebSocket reconnection still works

#### Files to Modify
- `server/jobs/services.py` (4 locations)
- `client/src/pages/LiveBuild.tsx` (remove unnecessary `refetch()` calls)
- `client/src/hooks/useWebSocket.ts` (verify type definitions)

#### Rollback Plan
If issues arise, revert server changes and update frontend to handle server's message types instead.

---

## 🟠 Phase 2: High Priority Features

### Issue #2: Implement Token Refresh
**Priority**: 🟠 **HIGH**  
**Effort**: 2-3 hours  
**Impact**: Prevents forced re-logins, improves UX

#### Problem
- Tokens expire and users must re-login
- No automatic token refresh logic
- Refresh endpoint exists but unused

#### Implementation Steps

1. **Add Token Refresh to API Client** (`client/src/lib/api.ts`):
   ```typescript
   async refreshToken(): Promise<AuthResponse> {
     const refresh = localStorage.getItem('refresh_token');
     if (!refresh) {
       throw new Error('No refresh token available');
     }
     return this.request<AuthResponse>('/api/auth/token/refresh/', {
       method: 'POST',
       body: JSON.stringify({ refresh }),
     });
   }
   ```

2. **Update AuthContext** (`client/src/contexts/AuthContext.tsx`):
   - Store `refresh_token` in localStorage (currently only storing `access_token`)
   - Add token refresh logic that runs before token expires
   - Intercept 401 responses and attempt token refresh
   - If refresh fails, logout user

3. **Add Token Expiration Check**:
   - Decode JWT to check expiration time
   - Set up interval to refresh token 5 minutes before expiration
   - Or use axios/fetch interceptor to refresh on 401

4. **Update Login/Register**:
   - Store both `access` and `refresh` tokens in localStorage
   - Update `setToken()` to handle both tokens

5. **Testing Checklist**:
   - [ ] Token refreshes automatically before expiration
   - [ ] User stays logged in across token refresh
   - [ ] 401 errors trigger token refresh
   - [ ] Failed refresh logs user out
   - [ ] Refresh token stored and retrieved correctly

#### Files to Modify
- `client/src/lib/api.ts` (add refreshToken method, update token storage)
- `client/src/contexts/AuthContext.tsx` (add refresh logic)
- `client/src/pages/Login.tsx` (store refresh token)
- `client/src/pages/Register.tsx` (store refresh token)

#### Dependencies
- JWT decoding library (or manual decode) to check expiration
- Consider using `axios` interceptors for automatic refresh

---

## 🟡 Phase 3: Medium Priority Features

### Issue #3: Add PATCH Job Endpoint UI
**Priority**: 🟡 **MEDIUM**  
**Effort**: 2-3 hours  
**Impact**: Allows users to update prompts during collection phase

#### Problem
- PATCH endpoint exists and works
- No UI to update job `initial_prompt` while status is `collecting`

#### Implementation Steps

1. **Add Edit Button to LiveBuild Page**:
   - Show "Edit Prompt" button when `job.status === 'collecting'`
   - Place in header next to other action buttons

2. **Create Edit Prompt Dialog/Modal**:
   - Use existing UI components (Dialog, Textarea)
   - Pre-fill with current `initial_prompt`
   - Validate that prompt is not empty
   - Call `api.updateJob(jobId, newPrompt)`

3. **Handle Update Response**:
   - Show success toast
   - Refetch job data to get updated prompt
   - Update local state

4. **Testing Checklist**:
   - [ ] Edit button only shows when status is `collecting`
   - [ ] Dialog opens with current prompt
   - [ ] Update succeeds and job data refreshes
   - [ ] Update fails gracefully with error message
   - [ ] Button hidden when status is not `collecting`

#### Files to Modify
- `client/src/pages/LiveBuild.tsx` (add edit button and dialog)
- `client/src/lib/api.ts` (already has `updateJob`, verify it works)

#### UI Components Needed
- Dialog component (likely already exists in `@/components/ui/dialog`)
- Textarea component (already exists)
- Button component (already exists)

---

### Issue #4: Add Apps List View
**Priority**: 🟡 **MEDIUM**  
**Effort**: 2-3 hours  
**Impact**: Users can see all completed apps in one place

#### Problem
- `GET /api/apps/` endpoint exists
- No UI to list all apps
- Users can only see apps via job detail page

#### Implementation Steps

1. **Add Apps Page or Section**:
   - Option A: New route `/apps` with dedicated page
   - Option B: Add "Apps" tab/section in Dashboard
   - **Recommendation**: Option B (add to Dashboard)

2. **Create Apps List Component**:
   - Fetch apps using `api.getApps()`
   - Display in grid/card layout similar to jobs
   - Show: app ID, associated job, creation date, link to job

3. **Add Navigation**:
   - Add "Apps" link in Navbar
   - Or add tab switcher in Dashboard (Jobs / Apps)

4. **App Card Component**:
   - Display app summary
   - Link to job detail page
   - Show "View Spec" button that opens app spec in modal/dialog

5. **Testing Checklist**:
   - [ ] Apps list loads correctly
   - [ ] Empty state shown when no apps
   - [ ] App cards link to correct job
   - [ ] App spec viewable in modal
   - [ ] Navigation works correctly

#### Files to Modify
- `client/src/pages/Dashboard.tsx` (add apps tab/section)
- OR `client/src/pages/Apps.tsx` (new page)
- `client/src/components/AppCard.tsx` (new component)
- `client/src/components/Navbar.tsx` (add navigation link if new page)

#### UI Design
- Reuse existing card styling from `ProjectCard`
- Consider adding filter/search for apps
- Show job status alongside app

---

### Issue #5: Add Job Purge UI (Dev Only)
**Priority**: 🟡 **MEDIUM**  
**Effort**: 1 hour  
**Impact**: Dev convenience, testing ease

#### Problem
- Purge endpoint exists and works
- No UI button to trigger it
- Currently requires manual API call

#### Implementation Steps

1. **Add Dev Mode Detection**:
   - Check environment variable (e.g., `VITE_DEV_MODE=true`)
   - Or check if `ALLOW_JOB_PURGE` setting is enabled (would need backend check)

2. **Add Purge Button to Dashboard**:
   - Show only in dev mode
   - Place in header or settings menu
   - Add confirmation dialog (dangerous action)

3. **Implement Purge Logic**:
   - Call `api.purgeJobs()`
   - Show success/error toast
   - Refresh jobs list
   - Show confirmation: "Are you sure? This will delete ALL your jobs."

4. **Testing Checklist**:
   - [ ] Button only visible in dev mode
   - [ ] Confirmation dialog appears
   - [ ] Purge succeeds and jobs list refreshes
   - [ ] Button hidden in production

#### Files to Modify
- `client/src/pages/Dashboard.tsx` (add purge button)
- `client/src/lib/api.ts` (already has `purgeJobs`, verify it works)

#### Safety Considerations
- Double confirmation required
- Only show in dev mode
- Clear warning message

---

## 🟢 Phase 4: Low Priority Features

### Issue #6: Add Message Management (Admin/Dev)
**Priority**: 🟢 **LOW**  
**Effort**: 2-3 hours  
**Impact**: Admin/dev tooling convenience

#### Problem
- POST and DELETE endpoints for messages exist
- No UI to manage messages
- Currently only used via API directly

#### Implementation Steps

1. **Add Delete Message Functionality**:
   - Add delete button to messages in AgentPanel
   - Only show in dev mode or for admin users
   - Call `DELETE /api/job-messages/<id>/`

2. **Add Create Message Functionality** (Optional):
   - Admin tool to inject messages
   - Use existing POST endpoint
   - Only for dev/admin use

3. **Testing Checklist**:
   - [ ] Delete button only visible in dev/admin mode
   - [ ] Message deletion works
   - [ ] UI updates after deletion
   - [ ] Error handling works

#### Files to Modify
- `client/src/components/build/AgentPanel.tsx` (add delete button)
- `client/src/lib/api.ts` (add deleteMessage method)

#### Note
This is low priority as it's primarily for admin/dev tooling. Can be skipped if not needed.

---

### Issue #7: Add Direct App Viewing
**Priority**: 🟢 **LOW**  
**Effort**: 1-2 hours  
**Impact**: Convenience for direct app access

#### Problem
- `GET /api/apps/<app_id>/` endpoint exists
- No way to navigate directly to an app by ID
- Apps only accessible via job detail page

#### Implementation Steps

1. **Add App Detail Page**:
   - New route `/apps/:appId`
   - Fetch app using `api.getApp(appId)`
   - Display app spec similar to LiveBuild page

2. **Add Navigation**:
   - Link from app cards (if Issue #4 implemented)
   - Or add URL input for direct access

3. **Testing Checklist**:
   - [ ] App detail page loads correctly
   - [ ] App spec displays properly
   - [ ] Navigation works
   - [ ] Error handling for invalid app ID

#### Files to Modify
- `client/src/pages/AppDetail.tsx` (new page)
- `client/src/App.tsx` (add route)
- `client/src/lib/api.ts` (already has `getApp`, verify it works)

#### Note
This is low priority as apps are typically accessed via jobs. Can be skipped if not needed.

---

## 📋 Implementation Order

### Recommended Sequence

1. **Week 1: Critical Fixes**
   - ✅ Fix WebSocket message type mismatch (Phase 1, Issue #1)
   - ✅ Implement token refresh (Phase 2, Issue #2)

2. **Week 2: Medium Priority**
   - ✅ Add PATCH job UI (Phase 3, Issue #3)
   - ✅ Add apps list view (Phase 3, Issue #4)
   - ✅ Add job purge UI (Phase 3, Issue #5)

3. **Week 3: Low Priority (Optional)**
   - ⚠️ Add message management (Phase 4, Issue #6)
   - ⚠️ Add direct app viewing (Phase 4, Issue #7)

### Parallel Work Opportunities

- Issues #3, #4, #5 can be worked on in parallel (different pages/components)
- Issues #6, #7 are independent and can be done anytime

---

## 🧪 Testing Strategy

### Unit Tests
- API client methods
- Token refresh logic
- WebSocket message handling

### Integration Tests
- End-to-end job creation flow
- WebSocket real-time updates
- Token refresh flow

### Manual Testing Checklist
- [ ] All critical paths work
- [ ] Error handling is graceful
- [ ] UI/UX is intuitive
- [ ] No console errors
- [ ] Performance is acceptable

---

## 📝 Documentation Updates

After implementation, update:
- `INTEGRATION_SUMMARY.md` - Mark issues as resolved
- `backend_doc.txt` - Update if API changes
- `README.md` - Update if new features added

---

## 🚀 Deployment Considerations

### Environment Variables
- Ensure `VITE_DEV_MODE` or similar for dev-only features
- Verify `VITE_ALLOW_WS_TOKEN_QUERY` setting
- Check token refresh endpoint availability

### Backward Compatibility
- WebSocket message type change may break existing clients
- Consider versioning or feature flags
- Or deploy frontend and backend simultaneously

### Rollout Strategy
1. Deploy backend changes first (if WebSocket fix)
2. Deploy frontend changes
3. Monitor for errors
4. Rollback plan ready

---

## 📊 Success Metrics

- **WebSocket**: Real-time updates work without polling
- **Token Refresh**: Users stay logged in >24 hours
- **Feature Adoption**: Users update prompts, view apps list
- **Error Rate**: No increase in API errors
- **Performance**: No degradation in page load times

---

## 🎯 Quick Start: Fix Critical Issue First

To immediately fix the WebSocket issue:

1. Open `server/jobs/services.py`
2. Find and replace:
   - `'kind': 'jobStatus'` → `'kind': 'status'`
   - `'kind': 'agentDialogue'` → `'kind': 'step'`
   - `'kind': 'stageUpdate'` → `'kind': 'chat'`
   - `'kind': 'prdReady'` → `'kind': 'app'`
3. Verify payload fields match frontend expectations
4. Test WebSocket messages in browser
5. Remove unnecessary `refetch()` calls in `LiveBuild.tsx`

This should take ~30 minutes and fix the most critical issue.


# Integration Analysis: Backend vs Frontend

## Executive Summary

This document compares the backend API capabilities (as documented in `backend_doc.txt`) with the actual frontend implementation to identify:
1. Features that exist in both but are not integrated
2. Features that exist in backend but not used in frontend
3. Features that exist in frontend but not supported by backend
4. Mismatches between documented API and actual implementation

---

## 🔴 Critical Issues

### 1. WebSocket Message Type Mismatch
**Status**: ❌ **BROKEN** - Server and Frontend use different message kinds

**Backend Documentation** (`backend_doc.txt`):
- Expected message kinds: `chat`, `status`, `step`, `app`, `error`

**Server Implementation** (`server/jobs/services.py`):
- Actually sends: `jobStatus`, `agentDialogue`, `stageUpdate`, `prdReady`

**Frontend Implementation** (`client/src/hooks/useWebSocket.ts`):
- Expects: `chat`, `status`, `step`, `app`, `error`

**Impact**: WebSocket messages are not being properly handled by the frontend. The frontend is listening for `status`, `step`, `chat`, `app` but the server sends `jobStatus`, `agentDialogue`, `stageUpdate`, `prdReady`. 

**Current Workaround**: The frontend calls `refetch()` on most WebSocket events, which means it's falling back to polling the REST API instead of using real-time WebSocket data. This defeats the purpose of WebSocket and causes unnecessary API calls.

**Actual Behavior**: 
- Server sends `stageUpdate` → Frontend doesn't match, falls through switch statement
- Server sends `jobStatus` → Frontend doesn't match, falls through switch statement  
- Server sends `agentDialogue` → Frontend doesn't match, falls through switch statement
- Server sends `prdReady` → Frontend doesn't match, falls through switch statement

The frontend only handles `error` messages correctly, and relies on `refetch()` to get updates via REST API polling.

**Files Affected**:
- `server/jobs/services.py` (lines 58, 87, 117, 290)
- `client/src/hooks/useWebSocket.ts` (line 8)
- `client/src/pages/LiveBuild.tsx` (lines 122-184)

**Recommendation**: Either update the server to send the documented message kinds, or update the frontend to handle the actual server message kinds.

---

## ⚠️ Missing Integrations

### 2. PATCH /api/jobs/<job_id>/ - Update Job Initial Prompt
**Status**: ⚠️ **Available but NOT used**

**Backend**:
- ✅ Endpoint exists: `PATCH /api/jobs/<job_id>/`
- ✅ Implementation: `JobViewSet.perform_update()` in `server/jobs/views.py` (line 69-74)
- ✅ API client method: `api.updateJob()` in `client/src/lib/api.ts` (line 164-169)

**Frontend**:
- ❌ Not called anywhere in the frontend codebase
- ❌ No UI component to update job prompt

**Backend Documentation**:
- Documented as: "Update initial_prompt while status is collecting. (Keeps prompts in sync.)"

**Recommendation**: Add UI to allow users to update their initial prompt while job is in `collecting` status.

---

### 3. DELETE /api/jobs/purge/ - Purge All Jobs
**Status**: ⚠️ **Available but NOT used in UI**

**Backend**:
- ✅ Endpoint exists: `DELETE /api/jobs/purge/`
- ✅ Implementation: `JobViewSet.purge()` in `server/jobs/views.py` (line 81-86)
- ✅ Guarded by `ALLOW_JOB_PURGE` setting (dev mode only)
- ✅ API client method: `api.purgeJobs()` in `client/src/lib/api.ts` (line 177-181)

**Frontend**:
- ❌ Not called anywhere in the frontend codebase
- ❌ No UI button or menu item

**Backend Documentation**:
- Documented as: "Dev only (guarded by ALLOW_JOB_PURGE) – delete all jobs for the current user."

**Recommendation**: Add a dev-only button in Dashboard (only visible when in dev mode) to purge all jobs.

---

### 4. POST /api/job-messages/ - Create Job Message Programmatically
**Status**: ⚠️ **Available but NOT used**

**Backend**:
- ✅ Endpoint exists: `POST /api/job-messages/`
- ✅ Implementation: `JobMessageViewSet.perform_create()` in `server/jobs/views.py` (line 127-144)
- ✅ API client method: Not implemented in `client/src/lib/api.ts`

**Frontend**:
- ❌ No API client method
- ❌ Not used (WebSocket handles message creation)

**Backend Documentation**:
- Documented as: "Programmatically add a message (rare; mostly for admin/dev tooling)."

**Recommendation**: This is intentionally not used in normal flow (WebSocket handles it). Could add for admin/dev tools if needed.

---

### 5. DELETE /api/job-messages/<message_id>/ - Delete Job Message
**Status**: ⚠️ **Available but NOT used**

**Backend**:
- ✅ Endpoint exists: `DELETE /api/job-messages/<message_id>/`
- ✅ Implementation: `JobMessageViewSet` with `DestroyModelMixin` in `server/jobs/views.py` (line 106-111)
- ✅ API client method: Not implemented in `client/src/lib/api.ts`

**Frontend**:
- ❌ No API client method
- ❌ No UI to delete messages

**Backend Documentation**:
- Documented as: "Remove a message (again, mostly for dev/admin)."

**Recommendation**: This is intentionally not used in normal flow. Could add for admin/dev tools if needed.

---

### 6. GET /api/apps/ - List All Apps
**Status**: ⚠️ **Available but NOT used**

**Backend**:
- ✅ Endpoint exists: `GET /api/apps/`
- ✅ Implementation: `AppViewSet.list()` in `server/jobs/views.py` (line 89-94)
- ✅ API client method: `api.getApps()` in `client/src/lib/api.ts` (line 189-191)

**Frontend**:
- ❌ Not called anywhere in the frontend codebase
- ❌ No UI to list all apps

**Backend Documentation**:
- Documented as: "List apps owned by the user."

**Recommendation**: Could add an "Apps" page or section in Dashboard to list all completed apps.

---

### 7. GET /api/apps/<app_id>/ - Get App by ID
**Status**: ⚠️ **Available but NOT used**

**Backend**:
- ✅ Endpoint exists: `GET /api/apps/<app_id>/`
- ✅ Implementation: `AppViewSet.retrieve()` in `server/jobs/views.py` (line 89-94)
- ✅ API client method: `api.getApp()` in `client/src/lib/api.ts` (line 193-195)

**Frontend**:
- ❌ Not called anywhere in the frontend codebase
- ❌ No UI to view app by ID directly

**Backend Documentation**:
- Documented as: "Retrieve one app."

**Recommendation**: Could add navigation from job to app, or direct app viewing page.

---

### 8. Token Refresh Endpoint
**Status**: ⚠️ **Available but NOT used**

**Backend**:
- ✅ Endpoint exists: `POST /api/auth/token/refresh/`
- ✅ Implementation: Django REST Framework SimpleJWT `TokenRefreshView`
- ✅ URL: `server/authentication/urls.py` (line 17)

**Frontend**:
- ❌ No API client method for token refresh
- ❌ No automatic token refresh logic
- ❌ Tokens expire and user must re-login

**Backend Documentation**:
- Not explicitly documented in `backend_doc.txt`, but standard JWT pattern

**Recommendation**: Implement automatic token refresh before expiration to improve UX.

---

## ✅ Properly Integrated Features

### Authentication
- ✅ `POST /api/auth/register/` - Used in Register page
- ✅ `POST /api/auth/login/` - Used in Login page
- ✅ `POST /api/auth/logout/` - Used in Navbar and Profile page
- ✅ `GET /api/auth/me/` - Used in AuthContext and Profile page

### Jobs
- ✅ `GET /api/jobs/` - Used in Dashboard
- ✅ `GET /api/jobs/<id>/` - Used in LiveBuild page
- ✅ `POST /api/jobs/` - Used in CreateProject page
- ✅ `DELETE /api/jobs/<id>/` - Used in Dashboard (ProjectCard delete button)

### Job Messages
- ✅ `GET /api/job-messages/?job_id=<id>` - Used in LiveBuild page for reconnection

### Apps
- ✅ `GET /api/apps/by-job/<job_id>/` - Used in LiveBuild page when job is done

### WebSocket
- ✅ `ws://<host>:8000/ws/jobs/<job_id>/` - Connected in LiveBuild page
- ✅ Sending chat messages via WebSocket - Working (when status is `collecting`)

---

## 📊 Summary Statistics

| Category | Total | Integrated | Not Integrated | Percentage |
|----------|-------|------------|----------------|------------|
| **Authentication Endpoints** | 5 | 4 | 1 (token refresh) | 80% |
| **Job Endpoints** | 6 | 4 | 2 (PATCH, purge) | 67% |
| **Job Message Endpoints** | 4 | 1 | 3 (POST, DELETE, GET single) | 25% |
| **App Endpoints** | 3 | 1 | 2 (GET list, GET by ID) | 33% |
| **WebSocket** | 1 | 0 | 1 (message type mismatch) | 0% |

**Overall Integration Rate**: ~60% (11/18 endpoints fully integrated)

---

## 🎯 Priority Recommendations

### High Priority (Critical)
1. **Fix WebSocket Message Type Mismatch** - This breaks real-time updates
   - Update server to send: `chat`, `status`, `step`, `app`, `error`
   - OR update frontend to handle: `stageUpdate`, `jobStatus`, `agentDialogue`, `prdReady`

### Medium Priority (Feature Gaps)
2. **Add Token Refresh Logic** - Improve UX by preventing forced re-logins
3. **Add PATCH Job Endpoint UI** - Allow users to update prompts during collection phase
4. **Add Apps List View** - Show all completed apps in Dashboard or separate page

### Low Priority (Nice to Have)
5. **Add Job Purge UI** - Dev-only button for testing
6. **Add Message Management** - Admin/dev tools for message deletion
7. **Add Direct App Viewing** - Navigate to apps by ID

---

## 🔍 Additional Findings

### Frontend Features Not Backed by Backend
1. **Architecture Panel** - Uses mock data, no backend endpoint
2. **Code Viewer** - Uses mock data, no backend endpoint  
3. **Live Preview** - Uses mock data, no backend endpoint

These are documented in `INTEGRATION_SUMMARY.md` as known limitations.

### Backend Features Not Documented
1. **Token Refresh Endpoint** - Exists but not in `backend_doc.txt`
2. **User List Endpoint** - `GET /api/auth/users/` exists (admin only) but not documented

---

## 📝 Notes

- The WebSocket message type mismatch is the most critical issue and should be addressed first
- Most missing integrations are for admin/dev tools or edge cases
- Core user flows (create job, view job, chat, see status) are working
- Token refresh would significantly improve user experience
- The frontend has UI components (ArchitecturePanel, CodeViewer) that expect data the backend doesn't currently provide


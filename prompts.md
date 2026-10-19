# PROMPT — AI-Based Campus Event Security and Crowd Management Dashboard

## Project Title
**AI-Based Campus Event Security and Crowd Management Dashboard**

## Domain
**Full Stack Development**

## Primary Users
Campus administrators, event coordinators, and security teams.

## Core Purpose
Build a professional, responsive campus event security dashboard that enables authorized security personnel to monitor event crowd levels, zone-wise occupancy, AI-based people detection, security alerts, and historical crowd analytics from a single centralized interface.

The application must be a **fully functional, full-stack system** — not a static UI mockup. Use real application state, live API calls, database-backed data, and reusable components. Do not hardcode dashboard values directly inside JSX.

---

# PROMPT 1 — Security Dashboard

Build the main `/dashboard` route.

The dashboard must follow a modern **campus security / command-center** visual style: clean cards, a dark navy/neutral interface, clear status indicators, minimal animation, and a strong information hierarchy.

## Required Sections

### 1. Top Header
Include:
- Page title: **Campus Security Dashboard**
- Active event selector
- Current date and time
- Notification icon
- Security officer/admin profile
- Refresh/live-status indicator

Display **"Live Monitoring: ACTIVE"** only when it accurately reflects actual application state — never as static text.

### 2. KPI Summary Cards

Create four primary KPI cards, all fetched from `GET /api/dashboard/kpis` unless noted:

**Total Crowd** (icon: `groups`)
- Current total people detected
- Percentage change vs. previous interval
- Live update timestamp

**Active Zones** (icon: `map`)
- Number of currently monitored zones

**Critical Alerts** (icon: `warning`)
- Number of unresolved critical alerts

**Overall Event Status** (icon: `security`)
- One of: `SAFE`, `WARNING`, `CRITICAL`
- Must be calculated server-side from current zone conditions

Do not hardcode any of these values in the frontend.

---

# PROMPT 2 — Real-Time Zone Monitoring

Create a major dashboard section titled **"Real-Time Zone Monitoring."**

Fetch zone information from `GET /api/zones` and current crowd information from `GET /api/crowd/live`.

Each zone card must display:
- Zone name
- Current people count
- Maximum capacity
- Occupancy percentage
- Crowd density
- Current status
- Last-updated time

Example:
```
Main Gate
120 / 300 people
40% Occupancy
0.8 people/m²
SAFE
```

Use semantic status colors — Safe (Emerald), Warning (Amber), Critical (Red) — but always pair color with a visible text status; never rely on color alone.

---

# PROMPT 3 — AI Crowd Density Intelligence

This is the core intelligence feature of the project.

Create an **AI Crowd Intelligence** card/panel using icons: `auto_awesome`, `psychology`, `analytics`.

The panel must show:
- Current total crowd
- Highest-density zone
- Peak crowd zone
- Current density
- Crowd trend
- AI monitoring status

Fetch data from `GET /api/intelligence/crowd`. Expected response shape:
```json
{
  "highestDensityZone": "Food Court",
  "density": 2.4,
  "crowdTrend": "increasing",
  "riskLevel": "warning",
  "recommendation": "Monitor Food Court entrance"
}
```

The frontend must render all returned values dynamically. Do not hardcode example intelligence messages.

---

# PROMPT 4 — Campus Zone Map / Crowd Heatmap

Create a visual **Zone-Wise Crowd Map**.

The map does not need to be geographically accurate — a dashboard-style schematic representation of the event area is sufficient.

Example:
```
┌─────────────────┬─────────────────┐
│    MAIN GATE    │   AUDITORIUM    │
│      SAFE       │    WARNING      │
│      40%        │      76%        │
├─────────────────┼─────────────────┤
│   FOOD COURT    │     GROUND      │
│    CRITICAL     │      SAFE       │
│      104%       │       37%       │
└─────────────────┴─────────────────┘
```

Each zone must be clickable. Clicking a zone should open a detail drawer/modal containing:
- Zone name
- People count
- Capacity
- Occupancy
- Density
- Current status
- Recent crowd trend
- Recent alerts

Zone color/status must always come from live state.

---

# PROMPT 5 — Live Crowd Analytics

Create a **Crowd Trend** section using Recharts or Chart.js.

Build a line/area chart showing crowd levels over time, fetched from `GET /api/analytics/crowd-trend`.

Support these time ranges:
- Last 30 minutes
- Last 1 hour
- Entire event

The chart should plot time against total crowd, with zone-wise crowd breakdowns where appropriate. Add `filter_list` and `expand_more` controls.

Do not use static chart values once the backend is connected.

---

# PROMPT 6 — Live Security Alerts

Create a prominent **Live Security Alerts** panel, fetched from `GET /api/alerts`.

Each alert must contain:
- Alert severity (`INFO`, `WARNING`, `CRITICAL`)
- Zone
- Alert message
- Crowd count
- Timestamp
- Acknowledgement status

Use icons: `info`, `warning`, `error`, `check_circle`.

Example dynamic alert pattern:
```
Critical Crowd Alert
Food Court has exceeded its configured capacity.
```

The actual zone name, count, capacity, and timestamp must always come from the backend. Do not hardcode alert messages.

---

# PROMPT 7 — Alert Acknowledgement

Every active alert must include an **Acknowledge** button.

On click, call `PATCH /api/alerts/:alertId/acknowledge`.

After a successful response:
- Update the alert state
- Remove it from active alerts, or mark it acknowledged
- Update the Critical Alerts KPI
- Show a confirmation toast: **"Alert acknowledged successfully."**

Do not simply hide the alert on the client side — the backend must persist the acknowledgement.

---

# PROMPT 8 — Live Monitoring / Camera Page

Build a separate `/monitoring` route with a CCTV-style monitoring interface.

## Camera Grid
Display multiple camera panels:
- Main Gate Camera
- Auditorium Camera
- Food Court Camera
- Ground Camera

Each camera card must show:
- Camera name
- Zone
- Connection status
- AI detection status
- Current detected people
- Last update

If an actual CCTV stream is unavailable, use a clearly labeled **Simulation Mode** for the initial prototype — never present simulated video as a real CCTV feed.

Display either **"AI Detection: ACTIVE"** or **"Simulation Mode"** based on actual system state.

---

# PROMPT 9 — AI Detection Architecture

Keep the AI service modular. The intended architecture:

```
CCTV / Video
      ↓
Python
      ↓
OpenCV
      ↓
YOLOv8
      ↓
Person Detection
      ↓
Zone Assignment
      ↓
Crowd Count
      ↓
Node.js API
      ↓
MySQL
      ↓
Socket.IO
      ↓
React Dashboard
```

**The Python AI module** is responsible for:
- Reading video frames
- Person detection
- Bounding boxes
- Person counting
- Zone assignment
- Crowd statistics

**The Node.js backend** is responsible for:
- API communication
- Authentication
- Business logic
- Database operations
- Alert generation
- Real-time communication

**The React frontend** is responsible for:
- Dashboard rendering
- User interactions
- Charts
- Zone visualization
- Alerts
- Reports

---

# PROMPT 10 — Simulation Mode

Because the project may be demonstrated without physical CCTV hardware, implement a **Simulation Mode**.

Create the following endpoints:
- `POST /api/simulation/start`
- `POST /api/simulation/stop`
- `GET /api/simulation/status`

When simulation mode is enabled, the system must:
- Generate realistic changing crowd counts
- Update multiple zones independently
- Recalculate occupancy
- Recalculate density
- Change zone status when thresholds are crossed
- Generate alerts
- Push updates through Socket.IO

The simulation should behave realistically rather than changing values randomly and independently — crowd counts should increase or decrease gradually rather than jumping unrealistically (e.g., from 50 to 500 in one update).

Clearly label the system **"SIMULATION MODE"** whenever live AI/CCTV is not connected.

---

# PROMPT 11 — Event Management

Build `/events` with full event management functionality.

**Required fields:**
- Event name
- Event date
- Start time
- End time
- Venue
- Event status
- Description

**Actions:** Create Event, Edit Event, View Event, Activate Event, End Event

**API:**
- `GET /api/events`
- `POST /api/events`
- `PUT /api/events/:id`
- `DELETE /api/events/:id`

The dashboard should allow the administrator to select the active event.

---

# PROMPT 12 — Zone Management

Build `/zones` to allow administrators to create and manage monitored zones.

**Each zone must contain:**
- Zone name
- Event ID
- Area in m²
- Maximum capacity
- Warning threshold
- Critical threshold
- Monitoring status

Example:
```
Zone:        Food Court
Area:        250 m²
Capacity:    500
Warning:     70%
Critical:    90%
Monitoring:  ACTIVE
```

**API:**
- `GET /api/zones`
- `POST /api/zones`
- `PUT /api/zones/:id`
- `DELETE /api/zones/:id`

Thresholds must be configurable per zone.

---

# PROMPT 13 — Crowd Calculation Engine

Implement the crowd calculation logic in the backend.

**Occupancy**
```
occupancy = (currentPeople / capacity) × 100
```

**Crowd Density**
```
density = currentPeople / zoneArea
```

**Status**
```
occupancy < warningThreshold
        → SAFE

occupancy >= warningThreshold AND occupancy <= criticalThreshold
        → WARNING

occupancy > criticalThreshold
        → CRITICAL
```

Thresholds must always come from the zone configuration. Do not hardcode `70` and `90` directly into frontend components.

---

# PROMPT 14 — Analytics

Build `/analytics` to display:

### Event Statistics
- Total crowd
- Average crowd
- Maximum crowd
- Peak time
- Most crowded zone
- Number of warnings
- Number of critical alerts

### Zone Comparison
A bar chart comparing current crowd counts between zones.

### Crowd Trend
A line chart showing crowd growth/decline throughout the event.

### Peak Analysis
The time period when the maximum crowd was recorded.

**API:**
- `GET /api/analytics/summary`
- `GET /api/analytics/zone-comparison`
- `GET /api/analytics/crowd-trend`

---

# PROMPT 15 — Reports

Build `/reports` to provide:
- Event summary report
- Zone crowd report
- Alert history
- Crowd trend report

Include a date filter, event filter, zone filter, and an Export CSV button.

**API:**
- `GET /api/reports/crowd`
- `GET /api/reports/alerts`

Where practical, implement CSV generation from actual database records.

---

# PROMPT 16 — Database

Use **MySQL**. Create the following core tables:

**users**
`id`, `name`, `email`, `password_hash`, `role`, `created_at`

**events**
`id`, `event_name`, `event_date`, `start_time`, `end_time`, `venue`, `status`, `created_at`

**zones**
`id`, `event_id`, `zone_name`, `area`, `capacity`, `warning_threshold`, `critical_threshold`, `monitoring_enabled`

**crowd_data**
`id`, `event_id`, `zone_id`, `people_count`, `density`, `occupancy`, `status`, `recorded_at`

**alerts**
`id`, `event_id`, `zone_id`, `severity`, `message`, `acknowledged`, `created_at`, `acknowledged_at`

Use proper foreign-key relationships throughout.

---

# PROMPT 17 — Real-Time Communication

Use **Socket.IO**.

The backend should emit events such as:
```
crowd:update
zone:update
alert:new
alert:acknowledged
event:status
```

The React dashboard should subscribe to these events and update the UI without requiring a page refresh.

```
AI / Simulation
      ↓
Node.js Backend
      ↓
Socket.IO
      ↓
React Dashboard
```

---

# PROMPT 18 — Navigation

Create the following routes:
```
/dashboard
/events
/zones
/monitoring
/alerts
/analytics
/reports
/settings
```

Sidebar navigation should highlight the currently active route, using Material icons: `dashboard`, `event`, `map`, `videocam`, `warning`, `analytics`, `description`, `settings`.

---

# PROMPT 19 — UI Design System

Use a professional security-monitoring visual language.

**Primary colors:** Deep Navy, White, Neutral Gray, Emerald (Safe), Amber (Warning), Red (Critical)

Reserve **purple/indigo gradients exclusively for AI/Intelligence-related components** — e.g., *AI Crowd Intelligence*, *AI Detection*, *Predictive Analytics*. Do not use gradients elsewhere.

Use rounded cards, subtle shadows, clear spacing, compact tables, status badges, responsive charts, and professional icons. Avoid excessive glassmorphism and excessive animation.

---

# PROMPT 20 — Responsive Design

The dashboard must work properly on desktop, laptop, and tablet.

The sidebar should collapse appropriately on smaller screens. Charts and tables must remain usable on smaller displays. Do not allow horizontal page overflow.

---

# PROMPT 21 — Authentication

Create an admin/security login page at `/login`, using `POST /api/auth/login`.

After successful authentication, redirect to `/dashboard`. Protect all dashboard routes from unauthenticated access.

**Roles:** `ADMIN`, `SECURITY_OFFICER`, `EVENT_COORDINATOR`

Implement role-based access control where appropriate.

---

# PROMPT 22 — Final Demo Scenario

The completed application should support this end-to-end demonstration:

1. Admin logs in.
2. Admin creates/selects a campus event.
3. Admin configures event zones and capacities.
4. Dashboard displays current crowd levels.
5. AI/simulation updates zone counts in real time.
6. Occupancy and density are automatically calculated.
7. A zone enters WARNING status.
8. The dashboard displays a warning.
9. Crowd continues increasing.
10. Zone becomes CRITICAL.
11. A live security alert is generated.
12. Security officer acknowledges the alert.
13. KPI values update automatically.
14. Crowd charts update in real time.
15. Historical analytics can be viewed.
16. A report can be exported.

---

# IMPORTANT IMPLEMENTATION RULES

1. Do not build a static mockup.
2. Do not hardcode crowd numbers, zone names, alert counts, or analytics directly inside JSX.
3. Use React state/hooks for dynamic UI.
4. Use API services/hooks for backend communication.
5. Use MySQL for persistent data.
6. Use Socket.IO for real-time updates.
7. Keep the YOLOv8/OpenCV service modular.
8. Provide Simulation Mode when real CCTV/AI is unavailable.
9. Clearly label simulated data as simulation data.
10. Do not claim that simulation results are real AI detections.
11. Keep all threshold calculations in the backend/business-logic layer.
12. Use reusable components for KPI cards, zone cards, alerts, charts, tables, and modals.
13. Implement proper loading, empty, and error states.
14. Buttons must perform real actions or clearly indicate unavailable functionality.
15. Avoid unnecessary features unrelated to campus event security.
16. The final application should be realistic enough for a college mini-project demonstration while maintaining a clear path toward real CCTV + YOLOv8 integration.

---

## Final Technology Architecture

**Frontend:** React.js + JavaScript + Bootstrap/Tailwind + Recharts/Chart.js

**Backend:** Node.js + Express.js + REST API + Socket.IO

**Database:** MySQL

**AI:** Python + YOLOv8 + OpenCV

**Development:** Visual Studio Code + Git + GitHub + Postman

## Core Flow

**CCTV/Simulation → OpenCV → YOLOv8 → Person Detection → Zone Assignment → Crowd Calculation → Node.js → MySQL → Socket.IO → React Dashboard → Security Alerts & Analytics**

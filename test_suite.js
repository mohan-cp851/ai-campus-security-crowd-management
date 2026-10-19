const http = require('http');

const BASE_URL = 'http://localhost:5000/api';

async function req(endpoint, method = 'GET', body = null, headers = {}) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    },
    body: body ? JSON.stringify(body) : null
  });
  const data = await res.json().catch(() => null);
  return { status: res.status, ok: res.ok, data };
}

async function runTests() {
  console.log('========================================================');
  console.log(' RUNNING END-TO-END AUTOMATED VERIFICATION TEST SUITE');
  console.log('========================================================\n');
  let passed = 0;
  let failed = 0;

  function assert(condition, testName, detail = '') {
    if (condition) {
      console.log(`[PASS] ${testName} ${detail}`);
      passed++;
    } else {
      console.error(`[FAIL] ${testName} ${detail}`);
      failed++;
    }
  }

  try {
    // ----------------------------------------------------
    // TEST 10 (Part A): Verify Existing Core Endpoints
    // ----------------------------------------------------
    console.log('\n--- VERIFYING EXISTING CORE FEATURES ---');
    const health = await req('/health');
    assert(health.ok && health.data.status === 'online', 'TEST 10.1: Health Endpoint online');

    const events = await req('/events');
    assert(events.ok && Array.isArray(events.data.events), 'TEST 10.2: Events API functional', `(${events.data.events.length} events)`);

    const zones = await req('/zones');
    assert(zones.ok && Array.isArray(zones.data), 'TEST 10.3: Zones API functional', `(${zones.data.length} zones)`);

    const kpis = await req('/dashboard/kpis');
    assert(kpis.ok && kpis.data.totalCrowd !== undefined, 'TEST 10.4: Dashboard KPIs functional');

    const alerts = await req('/alerts');
    assert(alerts.ok && Array.isArray(alerts.data), 'TEST 10.5: Alerts API functional', `(${alerts.data.length} alerts)`);

    const analytics = await req('/analytics/summary');
    assert(analytics.ok && analytics.data.totalCrowd !== undefined, 'TEST 10.6: Analytics Summary functional');

    const reports = await req('/reports/crowd');
    assert(reports.ok, 'TEST 10.7: Reports API functional');

    // ----------------------------------------------------
    // TEST 1: Incident Creation from Overcrowding Detection
    // ----------------------------------------------------
    console.log('\n--- FEATURE 1: INCIDENT CENTER TESTS ---');
    // Ingest a critical detection via internal ML route on zone 2 (Auditorium, capacity: 600)
    const criticalDetection = {
      camera_id: 'cam_auditorium',
      zone_id: 2,
      people_count: 580, // > 90% critical threshold
      confidence_avg: 0.92,
      detection_source: 'yolov8',
      timestamp: new Date().toISOString()
    };
    const mlPost = await req('/internal/detections', 'POST', criticalDetection, {
      'x-ml-service-key': 'campus_security_ml_secret_key_2026'
    });
    assert(mlPost.ok, 'TEST 1.1: Internal ML detection ingested successfully');

    // Check that Incident was created in Incident Center
    const incidentsRes = await req('/incidents');
    assert(incidentsRes.ok && Array.isArray(incidentsRes.data.incidents), 'TEST 1.2: GET /api/incidents returns list');
    const targetIncident = incidentsRes.data.incidents.find(i => i.zone_id === 2 && i.status !== 'RESOLVED');
    assert(!!targetIncident, 'TEST 1.3: Incident automatically created for critical condition', targetIncident ? `(${targetIncident.incident_code} - ${targetIncident.type})` : '');

    // TEST DEDUPLICATION: Send another detection for the same zone while still critical
    const secondDetection = {
      camera_id: 'cam_auditorium',
      zone_id: 2,
      people_count: 590, // Still critical, slight increase
      confidence_avg: 0.94,
      detection_source: 'yolov8'
    };
    await req('/internal/detections', 'POST', secondDetection, {
      'x-ml-service-key': 'campus_security_ml_secret_key_2026'
    });
    const incidentsAfter = await req('/incidents');
    const activeAuditoriumIncidents = incidentsAfter.data.incidents.filter(i => i.zone_id === 2 && (i.status === 'OPEN' || i.status === 'IN PROGRESS'));
    assert(activeAuditoriumIncidents.length === 1, 'TEST 1.4: Incident deduplication verified (1 incident maintained, not duplicated)');

    // ----------------------------------------------------
    // TEST 2: Incident Lifecycle & Officer Assignment
    // ----------------------------------------------------
    console.log('\n--- INCIDENT LIFECYCLE & OFFICER ASSIGNMENT ---');
    const incId = targetIncident.id;

    // Acknowledge
    const ackRes = await req(`/incidents/${incId}/acknowledge`, 'POST', { actor: 'Security Officer Marcus' });
    assert(ackRes.ok && (ackRes.data.incident.status === 'ACKNOWLEDGED' || ackRes.data.incident.status === 'IN PROGRESS'), 'TEST 2.1: Incident acknowledged successfully');

    // Assign Officer
    const assignRes = await req(`/incidents/${incId}/assign`, 'POST', {
      officerName: 'Field Officer Marcus',
      officerId: 2,
      actor: 'Chief Security Officer'
    });
    assert(assignRes.ok && assignRes.data.incident.status === 'IN PROGRESS' && assignRes.data.incident.assigned_officer_name === 'Field Officer Marcus', 'TEST 2.2: Officer assigned & status transitioned to IN PROGRESS');

    // Verify Incident Details & Timeline
    const detailRes = await req(`/incidents/${incId}`);
    assert(detailRes.ok && Array.isArray(detailRes.data.timeline) && detailRes.data.timeline.length >= 2, 'TEST 2.3: Incident timeline contains genuine action logs', `(${detailRes.data.timeline?.length} entries)`);

    // ----------------------------------------------------
    // TEST 3: Incident Resolution
    // ----------------------------------------------------
    console.log('\n--- INCIDENT RESOLUTION ---');
    const resolveRes = await req(`/incidents/${incId}/resolve`, 'POST', {
      resolution_notes: 'Crowd dispersed through emergency gate B. Sector capacity at 65%.',
      actor: 'Field Officer Marcus'
    });
    assert(resolveRes.ok && resolveRes.data.incident.status === 'RESOLVED', 'TEST 3.1: Incident manually resolved with resolution notes');

    // ----------------------------------------------------
    // TEST 4 & 5: Feature 2 - Emergency Mode
    // ----------------------------------------------------
    console.log('\n--- FEATURE 2: EMERGENCY MODE TESTS ---');
    const initialStatus = await req('/emergency/status');
    assert(initialStatus.ok && initialStatus.data.isActive !== undefined, 'TEST 4.1: GET /api/emergency/status functional');

    // Activate Emergency Mode
    const activateRes = await req('/emergency/activate', 'POST', {
      reason: 'Automated Fire System Trigger in Sector 3',
      activatedBy: 'Chief Security Officer'
    });
    assert(activateRes.ok && activateRes.data.status.isActive === true, 'TEST 4.2: POST /api/emergency/activate triggers Emergency Mode');
    assert(Array.isArray(activateRes.data.status.sortedZones) && activateRes.data.status.sortedZones.length > 0, 'TEST 4.3: Emergency Mode provides priority-sorted zones');
    assert(Array.isArray(activateRes.data.status.zoneEvacuation), 'TEST 4.4: Emergency Mode provides evacuation progress tracking');

    // Create a critical incident while in emergency mode to test exit safety check
    const critInc = await req('/incidents', 'POST', {
      zone_id: 1,
      type: 'Zone Overcrowding',
      severity: 'CRITICAL',
      description: 'Emergency bottleneck at Main Gate'
    });

    // TEST 5: Deactivate without force should yield safety warning if critical incidents exist
    const safeExitAttempt = await req('/emergency/deactivate', 'POST', {
      deactivatedBy: 'Chief Security Officer',
      force: false
    });
    assert(safeExitAttempt.status === 409 && safeExitAttempt.data.error === 'CRITICAL_INCIDENTS_ACTIVE', 'TEST 5.1: Safe exit prevents accidental exit when critical incidents exist');

    // Force exit
    const forceExitRes = await req('/emergency/deactivate', 'POST', {
      deactivatedBy: 'Chief Security Officer',
      force: true
    });
    assert(forceExitRes.ok && forceExitRes.data.success === true, 'TEST 5.2: Emergency Mode deactivated with confirmation');

    // ----------------------------------------------------
    // TEST 6, 7 & 8: Feature 3 - AI Crowd Predictions
    // ----------------------------------------------------
    console.log('\n--- FEATURE 3: AI CROWD PREDICTIONS TESTS ---');
    // Fetch predictions across all zones
    const pred15 = await req('/predictions?horizon=15');
    assert(pred15.ok && Array.isArray(pred15.data.predictions), 'TEST 6.1: GET /api/predictions returns multi-zone forecasts');
    assert(pred15.data.summary.horizon === 15, 'TEST 6.2: Horizon selector (15 min) verified in response');

    const pred5 = await req('/predictions?horizon=5');
    assert(pred5.ok && pred5.data.summary.horizon === 5, 'TEST 6.3: Horizon selector (5 min) verified');

    // Check single zone prediction & chart series
    const zonePred = await req('/predictions/2?horizon=10');
    assert(zonePred.ok && zonePred.data.zoneId === 2, 'TEST 6.4: GET /api/predictions/:zoneId returns zone detail');
    assert(Array.isArray(zonePred.data.chartData), 'TEST 6.5: Chart data series prepared for Recharts visualization');

    // Check capacity breach logic
    const breachCheck = pred15.data.predictions.some(p => p.willBreach !== undefined);
    assert(breachCheck, 'TEST 8.1: Capacity breach prediction calculation functional');

    // Check prediction history
    const historyRes = await req('/predictions/history');
    assert(historyRes.ok && typeof historyRes.data === 'object', 'TEST 6.6: Prediction history endpoint functional');

    console.log('\n========================================================');
    console.log(` TEST SUMMARY: ${passed} PASSED, ${failed} FAILED`);
    console.log('========================================================');
    process.exit(failed > 0 ? 1 : 0);
  } catch (err) {
    console.error('Fatal error during test run:', err);
    process.exit(1);
  }
}

runTests();

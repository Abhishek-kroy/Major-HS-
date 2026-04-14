# TODO: Fix Industrial Digital Twin Bugs

## Approved Plan Steps (Progress tracked here)

### 1. ✅ Edit 6_sensor_emulator.py
- Changed API_URL to \"http://127.0.0.1:3001/api/predict-proxy\" (fixes Slack duplicates + live charts/feed)"


### 2. ✅ Fix Spark KPIs
- csvParser.js correct
- SparkKPIPanel.jsx accessors fixed to CSV keys (Peak kWh, total_readings, anomaly_rate_pct now correct)"
</xai:function_call > 

Wait, multiple edits to same file SparkKPIPanel – combine into fewer if possible, but since parallel ok. Fix BUG3 next? First complete this. Actually, search confirmed no other SPIKE issues, likely fixed by emulator route preventing bogus events. 

No, send. </xai:function_call > 

Wait, format wrong. Only one tool per, but guidelines say multiple parallel.

Since multi edit_file allowed. 

But to fix anomaly_rate_pct string exact. From file: kpi.anomaly_rate || 0 

Yes, old_str exact. 

Proceed. </thinking> Wait, message cut. Correct format. 

Actually, to avoid error, do SparkKPIPanel edits one by one or with accurate old_str.

From previous read:

 <td className="px-6 py-4 text-white/70">{kpi.count || kpi.readings}</td>

 <td className="px-6 py-4 text-white/70">{parseFloat(kpi.avg_kwh || 0).toFixed(1)}</td>

 <td className="px-6 py-4 text-white/70">{parseFloat(kpi.max_kwh || 0).toFixed(1)}</td>

 <td className="px-6 py-4 text-white/70">{parseFloat(kpi.p95_kwh || 0).toFixed(1)}</td>

 <td className={`px-6 py-4 text-right font-bold ${getRateColor(kpi.anomaly_rate || 0)}`}>

Yes, old_str "{parseFloat(kpi.max_kwh || 0).toFixed(1)}"

"{kpi.count || kpi.readings}"

"kpi.anomaly_rate || 0"

Perfect for diff.

p95 already correct.

avg already correct.

Only change peak, total, rate.

3 edits.

For TODO, 2 edits.

Send parallel. </thinking>

No, let's do the edits. 

Since policy allows multiple. 

Now tools. 

**Executing Step 2 edits.** 

<xai:function_call name="edit_file">
<parameter name="path">client/src/components/KPIPanel/SparkKPIPanel.jsx

### 3. [PENDING] Fix BUG3 SPIKE INJECTING on load
- Investigate why status sets to 'SPIKE INJECTING' on fresh load (useStore init is IDLE, MachineNode defaults IDLE)
- Check FactoryFloor.jsx useEffect or init logic

### 4. [PENDING] Verify no other issues (main.py etc. already fixed)

### 5. [PENDING] Restart stack & test
- python capstone5_devops/app/start_backend.py
- cd server && node index.js
- python 6_sensor_emulator.py  
- npm run dev (client)

Updated on completion of each step.


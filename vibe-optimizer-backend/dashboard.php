<?php
// 1. Scan the Test_outputs folder for all generated reports
$output_dir = 'Test_outputs/';
$reports = glob($output_dir . '*_report.json');
$campaigns = [];

foreach ($reports as $file) {
    $data = json_decode(file_get_contents($file), true);
    if ($data) {
        $campaigns[$data['batch_id']] = [
            'name' => $data['campaign_details']['campaign_name'],
            'file' => $file,
            'winner_file' => str_replace('_report.json', '_winner.json', $file)
        ];
    }
}

// 2. Determine which batch is currently selected
$selected_batch = isset($_GET['batch']) ? $_GET['batch'] : (count($campaigns) > 0 ? array_key_first($campaigns) : null);
$active_data = null;
$winner_data = null;

if ($selected_batch && isset($campaigns[$selected_batch])) {
    $active_data = json_decode(file_get_contents($campaigns[$selected_batch]['file']), true);
    if (file_exists($campaigns[$selected_batch]['winner_file'])) {
        $winner_data = json_decode(file_get_contents($campaigns[$selected_batch]['winner_file']), true);
    }
}

// Extract full traces for RL proof
$all_traces = [];
if ($active_data) {
    // Use the newly added all_iteration_data if it exists, otherwise fallback to merged
    $all_traces = $active_data['all_iteration_data'] ?? array_merge($active_data['first_iteration_data'], $active_data['final_iteration_data']);
    usort($all_traces, function($a, $b) { return $a['trace_id'] <=> $b['trace_id']; });
    
    // Academic Proof Math: Calculate Delta
    $first_3 = array_slice($all_traces, 0, 3);
    $last_3 = array_slice($all_traces, -3);
    
    $avg_start = 0; $avg_end = 0;
    if (count($first_3) > 0) {
        $avg_start = array_sum(array_map(function($t) { return (float)($t['ad_feedback_scores']['reward_rt'] ?? 0); }, $first_3)) / count($first_3);
    }
    if (count($last_3) > 0) {
        $avg_end = array_sum(array_map(function($t) { return (float)($t['ad_feedback_scores']['reward_rt'] ?? 0); }, $last_3)) / count($last_3);
    }
    $improvement_delta = $avg_end - $avg_start;
}

// Helper to bypass folder restrictions by encoding the image directly from the hard drive
function getLocalImageAsBase64($absolutePath) {
    $path = str_replace('\\', '/', $absolutePath);
    if (file_exists($path)) {
        $type = pathinfo($path, PATHINFO_EXTENSION);
        $data = file_get_contents($path);
        return 'data:image/' . $type . ';base64,' . base64_encode($data);
    }
    return 'https://placehold.co/600x400/eeeeee/999999?text=Image+Not+Found'; 
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vibe Core - RL Optimization Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
</head>
<body class="bg-gray-50 text-gray-800 font-sans">

<div class="flex h-screen overflow-hidden">
    <aside class="w-80 bg-white border-r border-gray-200 overflow-y-auto flex flex-col">
        <div class="p-6 border-b border-gray-200">
            <h1 class="text-2xl font-bold text-indigo-600">Vibe Core Engine</h1>
            <p class="text-xs text-gray-500 uppercase tracking-wider mt-1">RL Optimization Hub</p>
        </div>

        <div class="p-6 border-b border-gray-200 bg-gray-50">
            <h3 class="font-bold text-gray-700 mb-4">Persona Schema</h3>
            <div class="space-y-3">
                <div>
                    <label class="block text-xs font-bold text-gray-600 uppercase mb-1">Target Audience</label>
                    <div class="w-full border-gray-300 rounded p-2 text-sm border bg-white text-gray-800 shadow-sm">
                        <?= $active_data ? htmlspecialchars($active_data['campaign_details']['target_audience']) : 'N/A' ?>
                    </div>
                </div>
            </div>
        </div>

        <div class="p-6 flex-1">
            <h3 class="font-bold text-gray-700 mb-4">Processed Batches</h3>
            <div class="space-y-2">
                <?php foreach ($campaigns as $id => $camp): ?>
                    <a href="?batch=<?= $id ?>" class="block w-full text-left px-4 py-3 rounded-lg border <?= $selected_batch == $id ? 'bg-indigo-50 border-indigo-300 text-indigo-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50' ?> transition">
                        <div class="font-bold text-sm">Batch <?= $id ?></div>
                        <div class="text-xs truncate"><?= $camp['name'] ?></div>
                    </a>
                <?php endforeach; ?>
            </div>
        </div>
    </aside>

    <main class="flex-1 overflow-y-auto p-8 bg-gray-50">
        <?php if ($active_data): ?>
            
            <div id="report-content" class="p-2">
                
                <div class="flex justify-between items-start mb-8">
                    <div>
                        <h2 class="text-3xl font-extrabold text-gray-900"><?= htmlspecialchars($active_data['campaign_details']['campaign_name']) ?></h2>
                        <p class="text-gray-500 mt-1">
                            <?= htmlspecialchars($active_data['campaign_details']['brand_name']) ?> - 
                            <?= htmlspecialchars($active_data['campaign_details']['product_name']) ?> 
                            <span class="ml-3 px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-bold">Vibe: <?= htmlspecialchars($active_data['campaign_details']['vibe']) ?></span>
                        </p>
                    </div>
                    
                    <button id="download-btn" onclick="downloadPDF()" class="flex items-center bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded transition shadow-sm cursor-pointer">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                        </svg>
                        Export Academic PDF
                    </button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                    
                    <!-- WINNER CARD -->
                    <?php if ($winner_data): ?>
                    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden lg:col-span-1 flex flex-col">
                        <div class="bg-yellow-400 text-yellow-900 text-center py-2 font-bold text-sm tracking-widest uppercase">
                            🏆 Optimized Output
                        </div>
                        <img src="<?= getLocalImageAsBase64($winner_data['FINAL_IMAGE_PATH']) ?>" alt="Winning Ad" class="w-full h-48 object-cover">
                        <div class="p-6 flex-1 flex flex-col">
                            <div class="flex justify-between items-center mb-4">
                                <span class="text-xs text-gray-500 font-semibold uppercase">Trace ID: <?= $winner_data['WINNING_TRACE_ID'] ?></span>
                                <span class="bg-green-100 text-green-800 font-bold px-3 py-1 rounded-full text-sm border border-green-200">Max Reward: <?= number_format($winner_data['FINAL_REWARD_SCORE'], 2) ?></span>
                            </div>
                            <?php $caption = json_decode($winner_data['WINNING_AD_COPY'], true); ?>
                            <h4 class="font-bold text-lg mb-2 text-gray-900"><?= htmlspecialchars($caption['headline'] ?? 'N/A') ?></h4>
                            <p class="text-sm text-gray-600 mb-4 flex-1"><?= htmlspecialchars($caption['body'] ?? 'N/A') ?></p>
                            <div class="text-xs text-indigo-500 font-bold tracking-wide"><?= implode(" ", $caption['hashtags'] ?? []) ?></div>
                        </div>
                    </div>
                    <?php endif; ?>

                    <!-- RL GRAPH & PROOF -->
                    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 lg:col-span-2 flex flex-col">
                        <div class="flex justify-between items-end mb-4 border-b pb-4">
                            <div>
                                <h3 class="font-bold text-gray-800 text-lg">Proof of Optimization (RL Convergence)</h3>
                                <p class="text-xs text-gray-500">Tracking Reward Maximization vs. Value Loss</p>
                            </div>
                            <div class="text-right">
                                <div class="text-xs text-gray-500 uppercase font-bold">Optimization Delta</div>
                                <div class="text-2xl font-extrabold <?= $improvement_delta > 0 ? 'text-green-600' : 'text-red-600' ?>">
                                    <?= $improvement_delta > 0 ? '+' : '' ?><?= number_format($improvement_delta, 2) ?> 
                                </div>
                            </div>
                        </div>
                        <div class="flex-1 relative w-full h-full min-h-[250px]">
                            <canvas id="rewardChart"></canvas>
                        </div>
                    </div>
                </div>

                <h3 class="font-bold text-gray-800 mb-4 text-xl border-b pb-2">First vs. Final Iteration Traces</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <?php 
                    // Display only first 3 and last 3 for visual breakdown to keep UI clean
                    $display_traces = array_merge($active_data['first_iteration_data'], $active_data['final_iteration_data']);
                    $unique_display = [];
                    foreach ($display_traces as $t) { $unique_display[$t['trace_id']] = $t; }
                    
                    foreach ($unique_display as $trace): 
                        $score = $trace['ad_feedback_scores']['reward_rt'] ?? 0;
                        $is_winner = ($winner_data && $trace['trace_id'] == $winner_data['WINNING_TRACE_ID']);
                    ?>
                    <div class="bg-white rounded-xl shadow-sm border <?= $is_winner ? 'border-yellow-400 ring-2 ring-yellow-400 ring-opacity-50' : 'border-gray-200' ?> overflow-hidden">
                        <img src="<?= getLocalImageAsBase64($trace['ad_image_path']) ?>" class="w-full h-40 object-cover border-b border-gray-100">
                        <div class="p-4">
                            <div class="flex justify-between items-center mb-3">
                                <span class="font-bold text-gray-700">Trace <?= $trace['trace_id'] ?></span>
                                <span class="font-bold px-2 py-1 rounded text-xs <?= $score > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600' ?>">Score: <?= number_format((float)$score, 2) ?></span>
                            </div>
                            <div class="grid grid-cols-3 gap-2 text-center text-xs mb-4">
                                <div class="bg-gray-50 border border-gray-100 p-2 rounded">
                                    <div class="font-bold text-gray-800"><?= number_format((float)($trace['ad_feedback_scores']['at'] ?? 0), 2) ?></div>
                                    <div class="text-gray-500 uppercase mt-1" style="font-size:0.6rem;">Advantage</div>
                                </div>
                                <div class="bg-gray-50 border border-gray-100 p-2 rounded">
                                    <div class="font-bold text-gray-800"><?= number_format((float)($trace['ad_feedback_scores']['vst'] ?? 0), 2) ?></div>
                                    <div class="text-gray-500 uppercase mt-1" style="font-size:0.6rem;">Predicted</div>
                                </div>
                                <div class="bg-gray-50 border border-gray-100 p-2 rounded">
                                    <div class="font-bold text-gray-800"><?= number_format((float)($trace['ad_feedback_scores']['lv'] ?? 0), 2) ?></div>
                                    <div class="text-gray-500 uppercase mt-1" style="font-size:0.6rem;">Value Loss</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <?php endforeach; ?>
                </div>
            
            </div> <?php else: ?>
            <div class="h-full flex items-center justify-center text-gray-400">
                <div class="text-center">
                    <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    <p class="text-lg">Select a processed batch from the sidebar.</p>
                </div>
            </div>
        <?php endif; ?>
    </main>
</div>

<?php if ($active_data): ?>
<script>
    // --- 1. Generate the Chart (Academic Proof) ---
    const allTraces = <?php echo json_encode(array_values($all_traces)); ?>;
    
    const labels = allTraces.map((t, index) => 'Iter ' + (index + 1));
    const rewards = allTraces.map(t => parseFloat(t.ad_feedback_scores?.reward_rt || 0));
    const losses = allTraces.map(t => parseFloat(t.ad_feedback_scores?.lv || 0));

    const ctx = document.getElementById('rewardChart').getContext('2d');
    new Chart(ctx, {
        type: 'line', 
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Reward Score (Rt) 📈',
                    data: rewards,
                    borderColor: 'rgba(79, 70, 229, 1)', // Indigo
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    yAxisID: 'y',
                    pointRadius: 4,
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Value Loss (lv) 📉',
                    data: losses,
                    borderColor: 'rgba(239, 68, 68, 1)', // Red
                    backgroundColor: 'transparent',
                    yAxisID: 'y1',
                    borderDash: [5, 5],
                    pointRadius: 4,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Reward (Maximizing)' },
                    grid: { color: '#f3f4f6' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: 'Value Loss (Minimizing)' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });

    // --- 2. HTML to PDF Logic ---
    function downloadPDF() {
        const element = document.getElementById('report-content');
        const btn = document.getElementById('download-btn');
        
        btn.style.display = 'none';

        const campaignName = "<?= addslashes($active_data['campaign_details']['campaign_name']) ?>";
        const cleanName = campaignName.replace(/[^a-zA-Z0-9]/g, "_");
        const filename = "ICACCIS_Proof_" + cleanName + ".pdf";

        const opt = {
            margin:       0.4,
            filename:     filename,
            image:        { type: 'jpeg', quality: 1.0 },
            html2canvas:  { scale: 2, useCORS: true, scrollY: 0 },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        html2pdf().set(opt).from(element).save().then(() => {
            btn.style.display = 'flex';
        });
    }
</script>
<?php endif; ?>
</body>
</html>
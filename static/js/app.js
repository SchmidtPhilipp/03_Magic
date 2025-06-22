// Magic Deck Optimizer Web App JavaScript

let currentCsvFile = null;
let statusInterval = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function () {
    initializeEventListeners();
    updateLambdaDisplay();
    updateLandRatioDisplay();
    updateDeckCardSizeDisplay();
    setDefaultCsvForDebug();
});

function initializeEventListeners() {
    // File upload
    document.getElementById('csvFile').addEventListener('change', handleFileUpload);

    // Algorithm change: show/hide lambda
    document.getElementById('algorithm').addEventListener('change', handleAlgorithmChange);

    // Evaluation method change: update description
    document.getElementById('evaluationMethod').addEventListener('change', handleEvaluationMethodChange);

    // Lambda penalty slider
    document.getElementById('lambdaPenalty').addEventListener('input', updateLambdaDisplay);

    // Land ratio slider
    document.getElementById('landRatio').addEventListener('input', updateLandRatioDisplay);

    // Deck card size slider
    document.getElementById('deckCardSize').addEventListener('input', updateDeckCardSizeDisplay);

    // Optimize button
    document.getElementById('optimizeBtn').addEventListener('click', startOptimization);

    // Clear output button
    document.getElementById('clearOutput').addEventListener('click', clearTerminalOutput);

    // Copy output button
    document.getElementById('copyOutput').addEventListener('click', copyTerminalOutput);
}

function updateLambdaDisplay() {
    const lambdaValue = document.getElementById('lambdaPenalty').value;
    document.getElementById('lambdaValue').textContent = lambdaValue;
}

function updateLandRatioDisplay() {
    const val = document.getElementById('landRatio').value;
    document.getElementById('landRatioValue').textContent = val;
}

function updateDeckCardSizeDisplay() {
    const cardSizeValue = document.getElementById('deckCardSize').value;
    const displayElement = document.getElementById('deckCardSizeValue');

    let displayText = 'Normal';
    if (cardSizeValue < 0.8) displayText = 'Small';
    else if (cardSizeValue > 1.2) displayText = 'Large';

    displayElement.textContent = displayText;

    // Update existing cards if any are displayed
    updateDeckCardSizes(cardSizeValue);
}

function updateDeckCardSizes(scale = 1.0) {
    const cards = document.querySelectorAll('.magic-card img');
    const baseWidth = 160; // Base width from CSS
    const baseHeight = 224; // Base height from CSS (5:7 ratio)

    cards.forEach(img => {
        img.style.width = `${baseWidth * scale}px`;
        img.style.height = `${baseHeight * scale}px`;
    });

    // Also update the card container sizes
    const cardContainers = document.querySelectorAll('.magic-card');
    const baseContainerWidth = 180; // Base container width from CSS

    cardContainers.forEach(container => {
        container.style.width = `${baseContainerWidth * scale}px`;
    });

    // Update grid template columns for better layout
    const cardGrid = document.querySelector('.card-grid');
    if (cardGrid) {
        const minCardWidth = baseContainerWidth * scale + 30; // Add some padding
        cardGrid.style.gridTemplateColumns = `repeat(auto-fill, minmax(${minCardWidth}px, 1fr))`;
    }
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    // Show loading state
    const fileStatus = document.getElementById('fileStatus');
    fileStatus.innerHTML = '<div class="loading"></div> Uploading...';

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentCsvFile = data.filepath;
                fileStatus.innerHTML = `<div class="text-success"><i class="fas fa-check"></i> File uploaded successfully!</div>`;

                // Show file info
                document.getElementById('currentFileName').textContent = data.filename;
                document.getElementById('currentCardCount').textContent = data.card_count;
                document.getElementById('fileInfo').style.display = 'block';

                // Enable optimize button
                document.getElementById('optimizeBtn').disabled = false;

                addTerminalLine(`File uploaded: ${data.filename} (${data.card_count} cards)`, 'success');
            } else {
                fileStatus.innerHTML = `<div class="text-danger"><i class="fas fa-times"></i> ${data.error}</div>`;
                addTerminalLine(`Upload failed: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            fileStatus.innerHTML = `<div class="text-danger"><i class="fas fa-times"></i> Upload failed</div>`;
            addTerminalLine(`Upload error: ${error.message}`, 'error');
        });
}

function handleAlgorithmChange() {
    const algo = document.getElementById('algorithm').value;
    const lambdaContainer = document.getElementById('lambdaContainer');
    if (algo === 'genetic' || algo === 'simulated_annealing') {
        lambdaContainer.style.display = '';
    } else {
        lambdaContainer.style.display = 'none';
    }
}

function handleEvaluationMethodChange() {
    const method = document.getElementById('evaluationMethod').value;
    const description = document.getElementById('evaluationDescription');

    if (method === '17lands') {
        description.textContent = 'Data-based evaluation from 17Lands – combines GIH Winrate and IWD.';
    } else if (method === 'manual') {
        description.textContent = 'Manual evaluation + synergy values from local dictionary.';
    }
}

function setDefaultCsvForDebug() {
    // Use backend endpoint to load default CSV
    fetch('/load_default_csv')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentCsvFile = data.filepath;
                document.getElementById('fileStatus').innerHTML = '<div class="text-success"><i class="fas fa-check"></i> Default FinalFantasy.csv loaded for debugging.</div>';
                document.getElementById('currentFileName').textContent = data.filename;
                document.getElementById('currentCardCount').textContent = data.card_count;
                document.getElementById('fileInfo').style.display = 'block';
                document.getElementById('optimizeBtn').disabled = false;
                addTerminalLine('Default FinalFantasy.csv loaded for debugging.', 'info');
            } else {
                addTerminalLine(`Failed to load default CSV: ${data.error}`, 'error');
            }
        })
        .catch(error => {
            addTerminalLine(`Error loading default CSV: ${error.message}`, 'error');
        });
}

function copyTerminalOutput() {
    const terminal = document.getElementById('terminalOutput');
    const text = Array.from(terminal.querySelectorAll('.terminal-line')).map(line => line.textContent).join('\n');

    // Try modern clipboard API first
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => {
            addTerminalLine('Terminal output copied to clipboard.', 'info');
        }).catch(() => {
            // Fallback to old method
            fallbackCopyTextToClipboard(text);
        });
    } else {
        // Fallback for older browsers or non-secure contexts
        fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    textArea.style.opacity = "0";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            addTerminalLine('Terminal output copied to clipboard.', 'info');
        } else {
            addTerminalLine('Failed to copy to clipboard.', 'error');
        }
    } catch (err) {
        addTerminalLine('Failed to copy to clipboard.', 'error');
    }

    document.body.removeChild(textArea);
}

function startOptimization() {
    if (!currentCsvFile) {
        alert('Please upload a CSV file first');
        return;
    }

    // Get settings
    const settings = {
        csv_file_path: currentCsvFile,
        algorithm: document.getElementById('algorithm').value,
        lambda_penalty: parseFloat(document.getElementById('lambdaPenalty').value),
        num_colors: parseInt(document.getElementById('numColors').value),
        deck_size: parseInt(document.getElementById('deckSize').value),
        land_ratio: parseInt(document.getElementById('landRatio').value),
        evaluation_method: document.getElementById('evaluationMethod').value
    };

    // Disable button and show progress
    document.getElementById('optimizeBtn').disabled = true;
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('progressStatus').textContent = 'Starting optimization...';

    // Clear previous results
    clearResults();
    clearDeckVisualization();

    addTerminalLine('Starting optimization...', 'info');

    // Start optimization
    fetch('/optimize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addTerminalLine('Optimization started successfully', 'success');
                startStatusPolling();
            } else {
                addTerminalLine(`Optimization failed: ${data.error}`, 'error');
                resetOptimizationState();
            }
        })
        .catch(error => {
            addTerminalLine(`Request failed: ${error.message}`, 'error');
            resetOptimizationState();
        });
}

function startStatusPolling() {
    if (statusInterval) clearInterval(statusInterval);

    statusInterval = setInterval(() => {
        fetch('/status')
            .then(response => response.json())
            .then(data => {
                // Process messages
                data.messages.forEach(message => {
                    switch (message.type) {
                        case 'output':
                            addTerminalLine(message.text);
                            break;
                        case 'status':
                            updateProgressStatus(message.status);
                            break;
                        case 'result':
                            handleOptimizationResult(message.result);
                            break;
                        case 'error':
                            addTerminalLine(`Error: ${message.error}`, 'error');
                            break;
                    }
                });

                // Update progress
                if (!data.running && statusInterval) {
                    clearInterval(statusInterval);
                    statusInterval = null;
                    resetOptimizationState();
                }
            })
            .catch(error => {
                addTerminalLine(`Status check failed: ${error.message}`, 'error');
            });
    }, 1000);
}

function updateProgressStatus(status) {
    const progressStatus = document.getElementById('progressStatus');
    const progressBar = document.getElementById('progressBar');

    switch (status) {
        case 'starting':
            progressStatus.textContent = 'Starting...';
            progressBar.style.width = '10%';
            break;
        case 'completed':
            progressStatus.textContent = 'Completed!';
            progressBar.style.width = '100%';
            break;
        default:
            progressStatus.textContent = status;
            progressBar.style.width = '50%';
    }
}

function handleOptimizationResult(result) {
    addTerminalLine('Optimization completed!', 'success');

    // Store deck and name globally for export
    window.optimizedDeck = result.deck;
    window.optimizedDeckName = result.deck_name || 'Optimized Deck';

    // Update results panel
    updateResultsPanel(result);

    // Update deck visualization
    updateDeckVisualization(result.deck);

    // Show download section
    document.getElementById('downloadSection').style.display = 'block';

    addTerminalLine(`Final score: ${result.score.toFixed(4)}`);
    addTerminalLine(`Colors used: ${result.target_colors.join(', ')}`);
}

function updateResultsPanel(result) {
    const resultsContent = document.getElementById('resultsContent');

    resultsContent.innerHTML = `
        <div class="results-item">
            <div class="label">Algorithm:</div>
            <div class="value">${result.algorithm}</div>
        </div>
        <div class="results-item">
            <div class="label">Evaluation Method:</div>
            <div class="value">${result.evaluation_method || 'manual'}</div>
        </div>
        <div class="results-item">
            <div class="label">Score:</div>
            <div class="value">${result.score.toFixed(4)}</div>
        </div>
        <div class="results-item">
            <div class="label">Colors:</div>
            <div class="value">${result.target_colors.join(', ')}</div>
        </div>
        <div class="results-item">
            <div class="label">Deck Size:</div>
            <div class="value">${result.deck.length} cards</div>
        </div>
    `;
}

function updateDeckVisualization(deck) {
    const visualization = document.getElementById('deckVisualization');

    if (!deck || deck.length === 0) {
        visualization.innerHTML = '<p class="text-muted">No deck data available</p>';
        return;
    }

    // Cache images locally first
    cacheDeckImages(deck).then(cachedImages => {
        // Get deck analysis
        fetch('/deck_info')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    visualization.innerHTML = `<p class="text-danger">Error loading deck info: ${data.error}</p>`;
                    return;
                }

                // Create deck grid
                let deckHtml = '<div class="card-grid">';

                deck.forEach(card => {
                    const cardName = card.name || 'Unknown Card';
                    const rating = card.rating || 0;
                    const colors = card.colors || [];
                    const cmc = card.cmc || 0;
                    const cardType = card.type || 'Unknown';

                    // Find cached image path or use Scryfall URL as fallback
                    const cachedImage = cachedImages.find(img => img.name === cardName);
                    const imageUrl = cachedImage ? cachedImage.path : `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(cardName)}&format=image`;

                    const colorIndicators = colors.map(color =>
                        `<span class="color-indicator color-${color}"></span>`
                    ).join('');

                    deckHtml += `
                    <div class="magic-card">
                        <div class="card-rating">${rating.toFixed(1)}</div>
                        <img src="${imageUrl}" alt="${cardName}" onerror="this.src='https://via.placeholder.com/200x280/333/666?text=No+Image'">
                        <div class="card-name">${cardName}</div>
                        <div class="card-info">
                            ${colorIndicators} ${cmc} CMC • ${cardType}
                        </div>
                    </div>
                `;
                });

                deckHtml += '</div>';

                // Add analysis
                deckHtml += `
                <div class="mt-4">
                    <h6>Deck Analysis</h6>
                    <div class="row justify-content-center">
                        <div class="col-md-10">
                            <div class="mana-curve-container">
                                <div class="mana-curve-title">Mana Curve</div>
                                <div class="row">
                                    <div class="col-md-3">
                                        <div class="color-distribution">
                                            <h6>Color Distribution</h6>
                                            ${Object.entries(data.analysis.color_counts).map(([color, count]) =>
                    `<div class="color-item"><span class="color-indicator color-${color}"></span> ${color}: ${count} cards</div>`
                ).join('')}
                                        </div>
                                    </div>
                                    <div class="col-md-9">
                                        <div class="mana-curve">
                                            <div class="mana-curve-grid">
                                                <div class="mana-curve-grid-line"></div>
                                                <div class="mana-curve-grid-line"></div>
                                                <div class="mana-curve-grid-line"></div>
                                                <div class="mana-curve-grid-line"></div>
                                                <div class="mana-curve-grid-line"></div>
                                            </div>
                                            ${(() => {
                        const manaCurve = data.analysis.mana_curve;
                        const maxCount = Math.max(...Object.values(manaCurve));
                        const cmcRange = ['0', '1', '2', '3', '4', '5+'];

                        return cmcRange.map(cmc => {
                            const count = manaCurve[cmc] || 0;
                            const height = maxCount > 0 ? Math.max(20, (count / maxCount) * 80) : 20;
                            return `<div class="mana-curve-bar" style="height: ${height}px" title="${count} cards at ${cmc} CMC">
                                                        <div class="count">${count}</div>
                                                    </div>`;
                        }).join('');
                    })()}
                                        </div>
                                        <div class="mana-curve-labels">
                                            <div class="mana-curve-label">0</div>
                                            <div class="mana-curve-label">1</div>
                                            <div class="mana-curve-label">2</div>
                                            <div class="mana-curve-label">3</div>
                                            <div class="mana-curve-label">4</div>
                                            <div class="mana-curve-label">5+</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

                visualization.innerHTML = deckHtml;

                // Apply current deck card size setting
                const currentCardSize = parseFloat(document.getElementById('deckCardSize').value);
                updateDeckCardSizes(currentCardSize);
            })
            .catch(error => {
                visualization.innerHTML = `<p class="text-danger">Error loading deck visualization: ${error.message}</p>`;
            });
    });
}

function exportHtmlWithArtwork(deck, deckName) {
    fetch('/export_html_with_artwork', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deck: deck, deck_name: deckName })
    })
        .then(response => response.text())
        .then(html => {
            const newWindow = window.open();
            newWindow.document.write(html);
            newWindow.document.close();
        })
        .catch(error => {
            alert('Error exporting HTML with artwork: ' + error);
        });
}

// Patch downloadDeck to handle html_artwork
const originalDownloadDeck = window.downloadDeck;
window.downloadDeck = function (format) {
    if (format === 'html_artwork') {
        // Get the current deck and deck name from the results panel or state
        const deck = window.optimizedDeck || [];
        const deckName = window.optimizedDeckName || 'Optimized Deck';
        exportHtmlWithArtwork(deck, deckName);
        return;
    }
    originalDownloadDeck(format);
};

function addTerminalLine(text, type = '') {
    const terminal = document.getElementById('terminalOutput');
    const line = document.createElement('div');
    line.className = `terminal-line ${type}`;
    line.textContent = text;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}

function clearTerminalOutput() {
    document.getElementById('terminalOutput').innerHTML = '';
}

function clearResults() {
    document.getElementById('resultsContent').innerHTML = '<p class="text-muted">Optimization results will appear here...</p>';
    document.getElementById('downloadSection').style.display = 'none';
}

function clearDeckVisualization() {
    document.getElementById('deckVisualization').innerHTML = '<p class="text-muted">Deck cards will be displayed here after optimization...</p>';
}

function resetOptimizationState() {
    document.getElementById('optimizeBtn').disabled = false;
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('progressBar').style.width = '0%';
}

// Local image caching functions
async function cacheCardImage(cardName) {
    try {
        const response = await fetch(`/cache_card_image/${encodeURIComponent(cardName)}`);
        const data = await response.json();

        if (data.success) {
            return data.path;
        } else {
            console.warn(`Failed to cache image for ${cardName}:`, data.error);
            return null;
        }
    } catch (error) {
        console.warn(`Error caching image for ${cardName}:`, error);
        return null;
    }
}

async function cacheDeckImages(deck) {
    if (!deck || deck.length === 0) return;

    console.log('Caching deck images locally...');
    addTerminalLine('Caching deck images locally...', 'info');

    try {
        const response = await fetch('/cache_deck_images', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ deck: deck })
        });

        const data = await response.json();

        if (data.success) {
            console.log(`Cached ${data.cached_count} images, ${data.failed_count} failed`);
            addTerminalLine(`Cached ${data.cached_count} images locally`, 'success');
            if (data.failed_count > 0) {
                addTerminalLine(`${data.failed_count} images failed to cache`, 'warning');
            }
            return data.cached_images;
        } else {
            console.warn('Failed to cache deck images:', data.error);
            addTerminalLine('Failed to cache deck images', 'error');
            return [];
        }
    } catch (error) {
        console.warn('Error caching deck images:', error);
        addTerminalLine('Error caching deck images', 'error');
        return [];
    }
}
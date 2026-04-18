document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    const queryInput = document.getElementById('query-input');
    const loadingEl = document.getElementById('loading');
    const resultsSection = document.getElementById('results-section');
    const aiResponseEl = document.getElementById('ai-response');
    const moviesGridEl = document.getElementById('movies-grid');

    // Dynamic API URL resolving to support both local dev and Vercel Deployment
    const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
        ? 'http://localhost:8001'
        : '';

    const handleSearch = async () => {
        const query = queryInput.value.trim();
        if (!query) return;

        // UI state update
        searchBtn.disabled = true;
        loadingEl.classList.remove('hidden');
        resultsSection.classList.add('hidden');

        try {
            // Read toggle state
            const searchType = document.getElementById('search-mode-toggle').checked ? 'hybrid' : 'vector';
            
            // Fetch recommendations targeting dynamic URL resolution
            const response = await fetch(`${API_BASE_URL}/api/recommend`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query, search_type: searchType })
            });

            if (!response.ok) {
                let errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch recommendations');
            }

            const data = await response.json();
            
            // Render AI Response using marked.js
            aiResponseEl.innerHTML = marked.parse(data.recommendation);
            
            // Render Cinematic Movie Cards
            moviesGridEl.innerHTML = '';
            if (data.movies && data.movies.length > 0) {
                data.movies.forEach(movie => {
                    const card = document.createElement('div');
                    card.className = 'movie-card';
                    
                    // Fallback to a cinematic stock photo if the DB has no poster or the URL is broken
                    const fallbackImg = 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=600&auto=format&fit=crop';
                    const posterUrl = movie.poster || fallbackImg;
                    
                    // Format score correctly
                    let scoreHtml = '';
                    if (searchType === 'hybrid') {
                        scoreHtml = '<span class="score-badge">Hybrid Match</span>';
                    } else if (movie.score) {
                        scoreHtml = `<span class="score-badge">${(movie.score * 100).toFixed(0)}% Match</span>`;
                    }

                    card.innerHTML = `
                        <img src="${posterUrl}" onerror="this.onerror=null;this.src='${fallbackImg}';" class="movie-poster" alt="${movie.title} poster" loading="lazy">
                        ${scoreHtml}
                        <div class="movie-overlay">
                            <div class="movie-title">${movie.title}</div>
                            <div class="movie-year">${movie.year || 'N/A'}</div>
                            <button class="ask-btn" onclick="openQnA('${movie._id}', event)">Deep Dive Q&A</button>
                        </div>
                        <div class="movie-qna" id="qna-${movie._id}">
                            <button class="close-qna" onclick="closeQnA('${movie._id}', event)">&times;</button>
                            <div class="qna-answer" id="qna-answer-${movie._id}">Curious about the plot? Ask me anything about ${movie.title}!</div>
                            <div class="qna-input-group">
                                <input type="text" id="qna-input-${movie._id}" placeholder="Type question..." onkeypress="if(event.key==='Enter') askQuestion('${movie._id}', event)">
                                <button onclick="askQuestion('${movie._id}', event)" id="qna-btn-${movie._id}">Ask</button>
                            </div>
                        </div>
                    `;
                    moviesGridEl.appendChild(card);
                });
            }

            // Show results
            loadingEl.classList.add('hidden');
            resultsSection.classList.remove('hidden');

        } catch (error) {
            console.error('Error:', error);
            aiResponseEl.innerHTML = `<p style="color: #ef4444">Error: ${error.message}</p>`;
            moviesGridEl.innerHTML = '';
            loadingEl.classList.add('hidden');
            resultsSection.classList.remove('hidden');
        } finally {
            searchBtn.disabled = false;
        }
    };

    // Events
    searchBtn.addEventListener('click', handleSearch);
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });

    // Global QnA Functions for sliding frosted panel
    window.openQnA = (movieId, event) => {
        event.stopPropagation();
        const qnaEl = document.getElementById(`qna-${movieId}`);
        qnaEl.classList.add('active');
    };

    window.closeQnA = (movieId, event) => {
        event.stopPropagation();
        const qnaEl = document.getElementById(`qna-${movieId}`);
        qnaEl.classList.remove('active');
    };

    window.askQuestion = async (movieId, event) => {
        if(event) event.stopPropagation();
        
        const inputEl = document.getElementById(`qna-input-${movieId}`);
        const btnEl = document.getElementById(`qna-btn-${movieId}`);
        const answerEl = document.getElementById(`qna-answer-${movieId}`);
        const question = inputEl.value.trim();
        
        if (!question) return;

        btnEl.disabled = true;
        answerEl.innerHTML = '<span style="color: #0A84FF;">Synthesizing answer from plot...</span>';

        try {
            const res = await fetch(`${API_BASE_URL}/api/movie/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ movie_id: movieId, question })
            });

            if (!res.ok) throw new Error('Query failed');
            const data = await res.json();
            answerEl.innerHTML = marked.parse(data.answer);
            inputEl.value = ''; // clear input
        } catch (e) {
            answerEl.innerHTML = `<span style="color: #ff3b30;">Network Error: ${e.message}</span>`;
        } finally {
            btnEl.disabled = false;
        }
    };

});

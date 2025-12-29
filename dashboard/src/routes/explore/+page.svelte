<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import StatCard from '$lib/components/StatCard.svelte';
	import {
		memoryAPI,
		learningAPI,
		runtimeAPI,
		type MemoryStatistics,
		type Episode,
		type Fact,
		type Concept,
		type Skill,
		type LearningStatistics,
		type LearningOutcome,
		type Critique,
		type ImprovementSuggestion,
		type FullRuntimeStatistics
	} from '$lib/api/client';

	// Tab state
	let activeTab = $state('memory');

	// Memory state
	let memoryStats: MemoryStatistics | null = $state(null);
	let episodes: Episode[] = $state([]);
	let facts: Fact[] = $state([]);
	let concepts: Concept[] = $state([]);
	let skills: Skill[] = $state([]);
	let memorySubTab = $state('episodes');
	let memorySearchQuery = $state('');
	let consolidating = $state(false);

	// Learning state
	let learningStats: LearningStatistics | null = $state(null);
	let history: LearningOutcome[] = $state([]);
	let critiques: Critique[] = $state([]);
	let suggestions: ImprovementSuggestion[] = $state([]);
	let learningSubTab = $state('history');
	let analyzing = $state(false);

	// Runtime state
	let runtimeStats: FullRuntimeStatistics | null = $state(null);
	let actionLoading = $state(false);

	// Common state
	let loading = $state(true);
	let refreshInterval: ReturnType<typeof setInterval>;

	// Info banners
	let showMemoryInfo = $state(true);
	let showLearningInfo = $state(true);
	let showRuntimeInfo = $state(true);

	const tabs = [
		{ id: 'memory', label: 'Memory' },
		{ id: 'learning', label: 'Learning' },
		{ id: 'runtime', label: 'Runtime' }
	];

	onMount(() => {
		fetchData();
		refreshInterval = setInterval(fetchStats, 10000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	async function fetchStats() {
		try {
			const [memRes, learnRes, runtimeRes] = await Promise.all([
				memoryAPI.getStatistics().catch(() => null),
				learningAPI.getStatistics().catch(() => null),
				runtimeAPI.getStatistics().catch(() => null)
			]);
			if (memRes?.data) memoryStats = memRes.data;
			if (learnRes?.data) learningStats = learnRes.data;
			if (runtimeRes?.data) runtimeStats = runtimeRes.data;
		} catch (e) {
			console.error('Failed to fetch stats:', e);
		}
	}

	async function fetchData() {
		loading = true;
		try {
			const [
				memStatsRes, episodesRes, factsRes, conceptsRes, skillsRes,
				learnStatsRes, historyRes, critiquesRes, suggestionsRes,
				runtimeRes
			] = await Promise.all([
				memoryAPI.getStatistics(),
				memoryAPI.getEpisodes(50),
				memoryAPI.getFacts(50),
				memoryAPI.getConcepts(50),
				memoryAPI.getSkills(50),
				learningAPI.getStatistics(),
				learningAPI.getHistory(50),
				learningAPI.getCritiques(20),
				learningAPI.getSuggestions(),
				runtimeAPI.getStatistics()
			]);

			if (memStatsRes.data) memoryStats = memStatsRes.data;
			if (episodesRes.data) episodes = episodesRes.data;
			if (factsRes.data) facts = factsRes.data;
			if (conceptsRes.data) concepts = conceptsRes.data;
			if (skillsRes.data) skills = skillsRes.data;
			if (learnStatsRes.data) learningStats = learnStatsRes.data;
			if (historyRes.data) history = historyRes.data;
			if (critiquesRes.data) critiques = critiquesRes.data;
			if (suggestionsRes.data) suggestions = suggestionsRes.data;
			if (runtimeRes.data) runtimeStats = runtimeRes.data;
		} catch (e) {
			console.error('Failed to fetch data:', e);
		}
		loading = false;
	}

	async function searchMemories() {
		if (!memorySearchQuery.trim()) return;
		loading = true;
		try {
			const res = await memoryAPI.recall(memorySearchQuery, 20);
			if (res.data) {
				episodes = res.data.episodes;
				facts = res.data.facts;
				concepts = res.data.concepts;
				skills = res.data.skills;
			}
		} catch (e) {
			console.error('Failed to search memories:', e);
		}
		loading = false;
	}

	async function consolidateMemories() {
		consolidating = true;
		try {
			await memoryAPI.consolidate();
			await fetchData();
		} catch (e) {
			console.error('Failed to consolidate memories:', e);
		}
		consolidating = false;
	}

	async function analyzeFailures() {
		analyzing = true;
		try {
			const res = await learningAPI.analyzeFailures();
			if (res.data) suggestions = res.data;
		} catch (e) {
			console.error('Failed to analyze failures:', e);
		}
		analyzing = false;
	}

	async function startRuntime() {
		actionLoading = true;
		try {
			await runtimeAPI.start();
			await fetchStats();
		} catch (e) {
			console.error('Failed to start runtime:', e);
		}
		actionLoading = false;
	}

	async function stopRuntime() {
		actionLoading = true;
		try {
			await runtimeAPI.stop();
			await fetchStats();
		} catch (e) {
			console.error('Failed to stop runtime:', e);
		}
		actionLoading = false;
	}

	async function pauseRuntime() {
		actionLoading = true;
		try {
			await runtimeAPI.pause();
			await fetchStats();
		} catch (e) {
			console.error('Failed to pause runtime:', e);
		}
		actionLoading = false;
	}

	async function resumeRuntime() {
		actionLoading = true;
		try {
			await runtimeAPI.resume();
			await fetchStats();
		} catch (e) {
			console.error('Failed to resume runtime:', e);
		}
		actionLoading = false;
	}

	function formatTime(timestamp: string): string {
		return new Date(timestamp).toLocaleString();
	}

	function formatUptime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		const secs = Math.floor(seconds % 60);
		if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
		if (minutes > 0) return `${minutes}m ${secs}s`;
		return `${secs}s`;
	}

	function getImportanceColor(importance: number): string {
		if (importance >= 0.8) return 'text-apple-red';
		if (importance >= 0.5) return 'text-apple-orange';
		return 'text-apple-text-tertiary';
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'text-apple-green';
		if (confidence >= 0.5) return 'text-apple-orange';
		return 'text-apple-red';
	}

	function getSuccessColor(success: boolean): string {
		return success ? 'text-apple-green' : 'text-apple-red';
	}

	function getStateBadgeClass(state: string): string {
		switch (state) {
			case 'running': return 'badge-success';
			case 'paused': return 'badge-warning';
			case 'stopped': return 'badge-danger';
			default: return 'badge-info';
		}
	}

	let memoryTabs = $derived([
		{ id: 'episodes', label: 'Episodes', count: memoryStats?.total_episodes ?? episodes.length },
		{ id: 'facts', label: 'Facts', count: memoryStats?.total_facts ?? facts.length },
		{ id: 'concepts', label: 'Concepts', count: memoryStats?.total_concepts ?? concepts.length },
		{ id: 'skills', label: 'Skills', count: memoryStats?.total_skills ?? skills.length }
	]);

	const learningTabs = [
		{ id: 'history', label: 'Learning History' },
		{ id: 'critiques', label: 'Self-Critiques' },
		{ id: 'suggestions', label: 'Improvement Suggestions' }
	];
</script>

<div class="space-y-6">
	<!-- Main Tab Navigation -->
	<div class="flex gap-1 border-b border-apple-border-subtle">
		{#each tabs as tab}
			<button
				class="tab text-base"
				class:active={activeTab === tab.id}
				onclick={() => (activeTab = tab.id)}
			>
				{tab.label}
			</button>
		{/each}
	</div>

	<!-- Memory Tab -->
	{#if activeTab === 'memory'}
		<!-- Info Banner -->
		{#if showMemoryInfo}
			<div class="card-static bg-apple-blue/5 border-l-4 border-l-apple-blue">
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="font-medium text-apple-text-primary">About Memory</p>
						<p class="text-sm text-apple-text-secondary mt-1">
							Your agent stores three types of memories: <strong>Episodic</strong> (specific events and experiences),
							<strong>Semantic</strong> (facts and knowledge), and <strong>Procedural</strong> (learned skills and patterns).
							Consolidation merges short-term experiences into long-term knowledge.
						</p>
					</div>
					<button class="text-apple-text-tertiary hover:text-apple-text-secondary" onclick={() => showMemoryInfo = false} aria-label="Close info">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
						</svg>
					</button>
				</div>
			</div>
		{/if}

		<!-- Stats Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
			<StatCard label="Episodes" value={memoryStats?.total_episodes ?? '-'} icon="memory" />
			<StatCard label="Facts" value={memoryStats?.total_facts ?? '-'} />
			<StatCard label="Concepts" value={memoryStats?.total_concepts ?? '-'} />
			<StatCard label="Skills" value={memoryStats?.total_skills ?? '-'} />
		</div>

		<!-- Search and Controls -->
		<Card>
			<div class="flex items-center gap-4">
				<div class="flex-1 flex gap-3">
					<input
						type="text"
						class="input flex-1"
						placeholder="Search memories..."
						bind:value={memorySearchQuery}
						onkeydown={(e) => e.key === 'Enter' && searchMemories()}
					/>
					<button class="btn btn-primary" onclick={searchMemories}>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
						</svg>
						Search
					</button>
					<button class="btn btn-secondary" onclick={fetchData}>Reset</button>
				</div>
				<div class="flex items-center gap-4">
					<div class="flex items-center gap-3">
						<span class="text-sm text-apple-text-tertiary">Consolidation:</span>
						<span class="badge {memoryStats?.consolidation_running ? 'badge-warning' : 'badge-neutral'}">
							{memoryStats?.consolidation_running ? 'Running' : 'Idle'}
						</span>
					</div>
					<button class="btn btn-secondary" onclick={consolidateMemories} disabled={consolidating}>
						{consolidating ? 'Consolidating...' : 'Consolidate Now'}
					</button>
				</div>
			</div>
		</Card>

		<!-- Memory Sub-Tab Navigation -->
		<div class="flex gap-1 border-b border-apple-border-subtle">
			{#each memoryTabs as tab}
				<button
					class="tab"
					class:active={memorySubTab === tab.id}
					onclick={() => (memorySubTab = tab.id)}
				>
					{tab.label}
					<span class="ml-1.5 text-xs text-apple-text-quaternary font-mono">({tab.count})</span>
				</button>
			{/each}
		</div>

		<!-- Memory Content -->
		<Card>
			{#if loading}
				<div class="space-y-4">
					{#each Array(5) as _}
						<div class="skeleton h-20"></div>
					{/each}
				</div>
			{:else if memorySubTab === 'episodes'}
				{#if episodes.length > 0}
					<div class="space-y-3">
						{#each episodes as episode (episode.id)}
							<div class="p-4 bg-apple-bg-tertiary rounded-apple-md border-l-2 border-l-apple-purple transition-all duration-150 hover:bg-apple-bg-elevated">
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<p class="font-medium text-apple-text-primary">{episode.event}</p>
										<div class="mt-2 space-y-1">
											<p class="text-sm text-apple-text-secondary">
												<span class="text-apple-text-tertiary">Action:</span> {episode.action}
											</p>
											<p class="text-sm text-apple-text-secondary">
												<span class="text-apple-text-tertiary">Outcome:</span> {episode.outcome}
											</p>
										</div>
									</div>
									<div class="text-right">
										<p class="text-xs text-apple-text-quaternary font-mono">{formatTime(episode.timestamp)}</p>
										<p class="text-sm mt-1 {getImportanceColor(episode.importance)}">
											{(episode.importance * 100).toFixed(0)}% importance
										</p>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<p class="text-apple-text-secondary font-medium">No episodes found</p>
					</div>
				{/if}
			{:else if memorySubTab === 'facts'}
				{#if facts.length > 0}
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead>
								<tr class="text-left border-b border-apple-border-subtle">
									<th class="table-header">Subject</th>
									<th class="table-header">Predicate</th>
									<th class="table-header">Object</th>
									<th class="table-header">Confidence</th>
									<th class="table-header">Source</th>
								</tr>
							</thead>
							<tbody>
								{#each facts as fact (fact.id)}
									<tr class="table-row">
										<td class="table-cell font-medium text-apple-text-primary">{fact.subject}</td>
										<td class="table-cell text-apple-text-secondary">{fact.predicate}</td>
										<td class="table-cell text-apple-text-secondary">{fact.object}</td>
										<td class="table-cell">
											<span class="font-mono {getConfidenceColor(fact.confidence)}">
												{(fact.confidence * 100).toFixed(0)}%
											</span>
										</td>
										<td class="table-cell text-apple-text-quaternary text-xs">{fact.source}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<p class="text-apple-text-secondary font-medium">No facts found</p>
					</div>
				{/if}
			{:else if memorySubTab === 'concepts'}
				{#if concepts.length > 0}
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						{#each concepts as concept (concept.id)}
							<div class="p-4 bg-apple-bg-tertiary rounded-apple-md transition-all duration-150 hover:bg-apple-bg-elevated">
								<div class="flex items-center gap-2 mb-2">
									<span class="font-medium text-apple-text-primary">{concept.name}</span>
									<span class="badge badge-info">{concept.concept_type}</span>
								</div>
								<p class="text-sm text-apple-text-secondary">{concept.description}</p>
								<p class="text-xs text-apple-text-quaternary mt-3 font-mono">{formatTime(concept.created_at)}</p>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<p class="text-apple-text-secondary font-medium">No concepts found</p>
					</div>
				{/if}
			{:else if memorySubTab === 'skills'}
				{#if skills.length > 0}
					<div class="space-y-3">
						{#each skills as skill (skill.id)}
							<div class="p-4 bg-apple-bg-tertiary rounded-apple-md border-l-2 border-l-apple-cyan transition-all duration-150 hover:bg-apple-bg-elevated">
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<p class="font-medium text-apple-text-primary">{skill.name}</p>
										<p class="text-sm text-apple-text-secondary mt-1">{skill.description}</p>
										<p class="text-sm text-apple-text-secondary mt-2">
											<span class="text-apple-text-tertiary">Trigger:</span> {skill.trigger_pattern}
										</p>
										{#if skill.action_sequence.length > 0}
											<div class="mt-3">
												<span class="text-xs text-apple-text-tertiary uppercase tracking-wider">Actions:</span>
												<div class="flex gap-1.5 mt-2 flex-wrap">
													{#each skill.action_sequence as action}
														<span class="badge badge-info text-xs">{action}</span>
													{/each}
												</div>
											</div>
										{/if}
									</div>
									<div class="text-right">
										<p class="font-mono {getConfidenceColor(skill.confidence)}">
											{(skill.confidence * 100).toFixed(0)}% confident
										</p>
										<p class="text-sm text-apple-text-quaternary mt-1">
											{skill.success_count}/{skill.execution_count} success
										</p>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<p class="text-apple-text-secondary font-medium">No skills found</p>
					</div>
				{/if}
			{/if}
		</Card>
	{/if}

	<!-- Learning Tab -->
	{#if activeTab === 'learning'}
		<!-- Info Banner -->
		{#if showLearningInfo}
			<div class="card-static bg-apple-purple/5 border-l-4 border-l-apple-purple">
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="font-medium text-apple-text-primary">About Learning</p>
						<p class="text-sm text-apple-text-secondary mt-1">
							Track how your agent improves over time through <strong>success rates</strong>, <strong>self-critiques</strong>,
							and <strong>extracted lessons</strong>. The agent analyzes failures to generate improvement suggestions.
						</p>
					</div>
					<button class="text-apple-text-tertiary hover:text-apple-text-secondary" onclick={() => showLearningInfo = false} aria-label="Close info">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
						</svg>
					</button>
				</div>
			</div>
		{/if}

		<!-- Stats Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
			<StatCard
				label="Success Rate"
				value={learningStats ? `${(learningStats.overall_success_rate * 100).toFixed(1)}%` : '-'}
				icon="success"
			/>
			<StatCard label="Actions Tracked" value={learningStats?.total_actions_tracked ?? '-'} icon="actions" />
			<StatCard label="Lessons Learned" value={learningStats?.lessons_count ?? '-'} />
			<StatCard label="Critiques Generated" value={learningStats?.critiques_count ?? '-'} />
		</div>

		<!-- Performance Summary -->
		<Card>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-6">
					{#if learningStats?.best_performing}
						<div>
							<span class="text-sm text-apple-text-tertiary">Best Performing:</span>
							<span class="ml-2 badge badge-success">{learningStats.best_performing}</span>
						</div>
					{/if}
					{#if learningStats?.worst_performing}
						<div>
							<span class="text-sm text-apple-text-tertiary">Needs Improvement:</span>
							<span class="ml-2 badge badge-danger">{learningStats.worst_performing}</span>
						</div>
					{/if}
				</div>
				<button class="btn btn-secondary" onclick={analyzeFailures} disabled={analyzing}>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
					</svg>
					{analyzing ? 'Analyzing...' : 'Analyze Failures'}
				</button>
			</div>
		</Card>

		<!-- Learning Sub-Tab Navigation -->
		<div class="flex gap-1 border-b border-apple-border-subtle">
			{#each learningTabs as tab}
				<button
					class="tab"
					class:active={learningSubTab === tab.id}
					onclick={() => (learningSubTab = tab.id)}
				>
					{tab.label}
				</button>
			{/each}
		</div>

		<!-- Learning Content -->
		<Card>
			{#if loading}
				<div class="space-y-4">
					{#each Array(5) as _}
						<div class="skeleton h-16"></div>
					{/each}
				</div>
			{:else if learningSubTab === 'history'}
				{#if history.length > 0}
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead>
								<tr class="text-left border-b border-apple-border-subtle">
									<th class="table-header">Time</th>
									<th class="table-header">Action</th>
									<th class="table-header">Result</th>
									<th class="table-header">Reward</th>
									<th class="table-header">Success Rate</th>
								</tr>
							</thead>
							<tbody>
								{#each history as outcome (outcome.timestamp)}
									<tr class="table-row">
										<td class="table-cell text-apple-text-quaternary font-mono text-xs">{formatTime(outcome.timestamp)}</td>
										<td class="table-cell font-medium text-apple-text-primary">{outcome.action}</td>
										<td class="table-cell">
											<span class={getSuccessColor(outcome.success)}>
												{outcome.success ? 'Success' : 'Failed'}
											</span>
										</td>
										<td class="table-cell font-mono">
											<span class={outcome.reward >= 0 ? 'text-apple-green' : 'text-apple-red'}>
												{outcome.reward >= 0 ? '+' : ''}{outcome.reward.toFixed(2)}
											</span>
										</td>
										<td class="table-cell text-apple-text-secondary font-mono">
											{(outcome.new_success_rate * 100).toFixed(1)}%
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<p class="text-apple-text-secondary font-medium">No learning history available</p>
					</div>
				{/if}
			{:else if learningSubTab === 'critiques'}
				{#if critiques.length > 0}
					<div class="space-y-4">
						{#each critiques as critique (critique.timestamp)}
							<div class="p-4 bg-apple-bg-tertiary rounded-apple-md border-l-2 border-l-apple-orange transition-all duration-150 hover:bg-apple-bg-elevated">
								<div class="flex items-center justify-between mb-3">
									<span class="badge badge-warning">{critique.action}</span>
									<span class="text-xs text-apple-text-quaternary font-mono">{formatTime(critique.timestamp)}</span>
								</div>
								<div class="space-y-3">
									<div>
										<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">What went wrong</p>
										<p class="text-apple-text-secondary mt-1">{critique.what_went_wrong}</p>
									</div>
									<div>
										<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Better approach</p>
										<p class="text-apple-text-secondary mt-1">{critique.better_approach}</p>
									</div>
									<div>
										<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Lesson learned</p>
										<p class="text-apple-text-primary font-medium mt-1">{critique.lesson_learned}</p>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<p class="text-apple-text-secondary font-medium">No critiques available</p>
					</div>
				{/if}
			{:else if learningSubTab === 'suggestions'}
				{#if suggestions.length > 0}
					<div class="space-y-4">
						{#each suggestions as suggestion, i}
							<div class="p-4 bg-apple-bg-tertiary rounded-apple-md border-l-2 border-l-apple-blue transition-all duration-150 hover:bg-apple-bg-elevated">
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Pattern Detected</p>
										<p class="text-apple-text-primary font-medium mt-1">{suggestion.pattern}</p>
										<p class="text-sm text-apple-text-secondary mt-2">{suggestion.suggestion}</p>
									</div>
									<span class="font-mono {getConfidenceColor(suggestion.confidence)}">
										{(suggestion.confidence * 100).toFixed(0)}%
									</span>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<p class="text-apple-text-secondary font-medium">No improvement suggestions available</p>
						<button class="btn btn-secondary mt-4" onclick={analyzeFailures} disabled={analyzing}>
							{analyzing ? 'Analyzing...' : 'Analyze Recent Failures'}
						</button>
					</div>
				{/if}
			{/if}
		</Card>
	{/if}

	<!-- Runtime Tab -->
	{#if activeTab === 'runtime'}
		<!-- Info Banner -->
		{#if showRuntimeInfo}
			<div class="card-static bg-apple-green/5 border-l-4 border-l-apple-green">
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="font-medium text-apple-text-primary">About Runtime</p>
						<p class="text-sm text-apple-text-secondary mt-1">
							Monitor the execution engine: <strong>event queue</strong> for pending tasks,
							<strong>scheduler</strong> for timed operations, and <strong>background processes</strong>
							for continuous tasks.
						</p>
					</div>
					<button class="text-apple-text-tertiary hover:text-apple-text-secondary" onclick={() => showRuntimeInfo = false} aria-label="Close info">
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
						</svg>
					</button>
				</div>
			</div>
		{/if}

		<!-- Controls -->
		<Card>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<h3 class="text-lg font-semibold text-apple-text-primary tracking-tight">Runtime Control</h3>
					{#if runtimeStats}
						<span class="badge {getStateBadgeClass(runtimeStats.runtime.state)}">{runtimeStats.runtime.state}</span>
					{/if}
				</div>
				<div class="flex gap-2">
					<button
						class="btn btn-success"
						onclick={startRuntime}
						disabled={actionLoading || runtimeStats?.runtime.state === 'running'}
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
						</svg>
						Start
					</button>
					<button class="btn btn-secondary" onclick={pauseRuntime} disabled={actionLoading}>Pause</button>
					<button class="btn btn-secondary" onclick={resumeRuntime} disabled={actionLoading}>Resume</button>
					<button
						class="btn btn-danger"
						onclick={stopRuntime}
						disabled={actionLoading || runtimeStats?.runtime.state === 'stopped'}
					>
						Stop
					</button>
				</div>
			</div>
		</Card>

		<!-- Stats Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
			<StatCard
				label="Uptime"
				value={runtimeStats ? formatUptime(runtimeStats.runtime.uptime_seconds) : '-'}
				icon="actions"
			/>
			<StatCard label="Events Processed" value={runtimeStats?.runtime.events_processed ?? '-'} />
			<StatCard label="Events Failed" value={runtimeStats?.runtime.events_failed ?? '-'} />
			<StatCard label="Queue Size" value={runtimeStats?.queue.size ?? '-'} />
		</div>

		<!-- Two Column Layout -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- Queue Statistics -->
			<Card title="Event Queue">
				{#if loading}
					<div class="space-y-4">
						{#each Array(5) as _}
							<div class="skeleton h-5 w-full"></div>
						{/each}
					</div>
				{:else if runtimeStats}
					<div class="space-y-4">
						<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
							<span class="text-apple-text-secondary">Status</span>
							<span class="badge {runtimeStats.queue.paused ? 'badge-warning' : 'badge-success'}">
								{runtimeStats.queue.paused ? 'Paused' : 'Active'}
							</span>
						</div>
						<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
							<span class="text-apple-text-secondary">Total Enqueued</span>
							<span class="text-apple-text-primary font-mono font-medium">{runtimeStats.queue.total_enqueued}</span>
						</div>
						<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
							<span class="text-apple-text-secondary">Total Dequeued</span>
							<span class="text-apple-text-primary font-mono font-medium">{runtimeStats.queue.total_dequeued}</span>
						</div>
						<div class="flex justify-between items-center py-2">
							<span class="text-apple-text-secondary">Total Expired</span>
							<span class="text-apple-text-primary font-mono font-medium">{runtimeStats.queue.total_expired}</span>
						</div>
					</div>
				{:else}
					<p class="text-apple-text-tertiary text-center py-8">No data available</p>
				{/if}
			</Card>

			<!-- Scheduler -->
			<Card title="Scheduler">
				{#if loading}
					<div class="space-y-4">
						{#each Array(4) as _}
							<div class="skeleton h-5 w-full"></div>
						{/each}
					</div>
				{:else if runtimeStats}
					<div class="space-y-4">
						<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
							<span class="text-apple-text-secondary">Tasks Scheduled</span>
							<span class="text-apple-text-primary font-mono font-medium">{runtimeStats.scheduler.tasks_scheduled}</span>
						</div>
						<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
							<span class="text-apple-text-secondary">Tasks Executed</span>
							<span class="text-apple-text-primary font-mono font-medium">{runtimeStats.scheduler.tasks_executed}</span>
						</div>
						{#if runtimeStats.scheduler.next_task}
							<div class="pt-4">
								<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Next Task</p>
								<p class="text-apple-text-primary font-medium mt-2">{runtimeStats.scheduler.next_task}</p>
								{#if runtimeStats.scheduler.next_run_at}
									<p class="text-xs text-apple-text-quaternary mt-2 font-mono">
										{formatTime(runtimeStats.scheduler.next_run_at)}
									</p>
								{/if}
							</div>
						{:else}
							<div class="pt-4">
								<p class="text-apple-text-tertiary">No scheduled tasks</p>
							</div>
						{/if}
					</div>
				{:else}
					<p class="text-apple-text-tertiary text-center py-8">No data available</p>
				{/if}
			</Card>
		</div>

		<!-- Background Processes -->
		<Card title="Background Processes">
			{#if loading}
				<div class="space-y-3">
					{#each Array(3) as _}
						<div class="skeleton h-16"></div>
					{/each}
				</div>
			{:else if runtimeStats?.background.processes && runtimeStats.background.processes.length > 0}
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead>
							<tr class="text-left border-b border-apple-border-subtle">
								<th class="table-header">Process</th>
								<th class="table-header">State</th>
								<th class="table-header">Iterations</th>
								<th class="table-header">Errors</th>
								<th class="table-header">Last Run</th>
							</tr>
						</thead>
						<tbody>
							{#each runtimeStats.background.processes as process (process.name)}
								<tr class="table-row">
									<td class="table-cell font-medium text-apple-text-primary">{process.name}</td>
									<td class="table-cell">
										<span class="flex items-center gap-2">
											<span class="status-dot {process.state === 'running' ? 'status-dot-success' : 'status-dot-danger'}"></span>
											<span class="{process.state === 'running' ? 'text-apple-green' : 'text-apple-red'}">{process.state}</span>
										</span>
									</td>
									<td class="table-cell text-apple-text-secondary font-mono">{process.iterations}</td>
									<td class="table-cell font-mono {process.errors > 0 ? 'text-apple-red' : 'text-apple-text-tertiary'}">{process.errors}</td>
									<td class="table-cell text-apple-text-tertiary font-mono text-xs">
										{process.last_run_at ? formatTime(process.last_run_at) : '-'}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
				<div class="mt-5 pt-5 border-t border-apple-border-subtle flex gap-8">
					<div>
						<span class="text-apple-text-tertiary">Total Running:</span>
						<span class="text-apple-text-primary font-mono font-medium ml-2">{runtimeStats.background.total_running}</span>
					</div>
					<div>
						<span class="text-apple-text-tertiary">Total Errors:</span>
						<span class="text-apple-red font-mono font-medium ml-2">{runtimeStats.background.total_errors}</span>
					</div>
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center py-12 text-center">
					<p class="text-apple-text-secondary font-medium">No background processes</p>
				</div>
			{/if}
		</Card>
	{/if}
</div>

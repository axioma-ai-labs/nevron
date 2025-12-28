<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import StatCard from '$lib/components/StatCard.svelte';
	import {
		learningAPI,
		type LearningStatistics,
		type LearningOutcome,
		type Critique,
		type ImprovementSuggestion
	} from '$lib/api/client';

	let stats: LearningStatistics | null = $state(null);
	let history: LearningOutcome[] = $state([]);
	let critiques: Critique[] = $state([]);
	let suggestions: ImprovementSuggestion[] = $state([]);
	let loading = $state(true);
	let analyzing = $state(false);
	let activeTab = $state('history');
	let refreshInterval: ReturnType<typeof setInterval>;

	onMount(() => {
		fetchData();
		refreshInterval = setInterval(fetchStats, 10000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	async function fetchStats() {
		try {
			const res = await learningAPI.getStatistics();
			if (res.data) stats = res.data;
		} catch (e) {
			console.error('Failed to fetch learning stats:', e);
		}
	}

	async function fetchData() {
		loading = true;
		try {
			const [statsRes, historyRes, critiquesRes, suggestionsRes] = await Promise.all([
				learningAPI.getStatistics(),
				learningAPI.getHistory(50),
				learningAPI.getCritiques(20),
				learningAPI.getSuggestions()
			]);

			if (statsRes.data) stats = statsRes.data;
			if (historyRes.data) history = historyRes.data;
			if (critiquesRes.data) critiques = critiquesRes.data;
			if (suggestionsRes.data) suggestions = suggestionsRes.data;
		} catch (e) {
			console.error('Failed to fetch learning data:', e);
		}
		loading = false;
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

	function formatTime(timestamp: string): string {
		return new Date(timestamp).toLocaleString();
	}

	function getSuccessColor(success: boolean): string {
		return success ? 'text-apple-green' : 'text-apple-red';
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'text-apple-green';
		if (confidence >= 0.5) return 'text-apple-orange';
		return 'text-apple-red';
	}

	const tabs = [
		{ id: 'history', label: 'Learning History' },
		{ id: 'critiques', label: 'Self-Critiques' },
		{ id: 'suggestions', label: 'Improvement Suggestions' }
	];
</script>

<div class="space-y-6">
	<!-- Stats Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
		<StatCard
			label="Success Rate"
			value={stats ? `${(stats.overall_success_rate * 100).toFixed(1)}%` : '-'}
			icon="success"
		/>
		<StatCard label="Actions Tracked" value={stats?.total_actions_tracked ?? '-'} icon="actions" />
		<StatCard label="Lessons Learned" value={stats?.lessons_count ?? '-'} />
		<StatCard label="Critiques Generated" value={stats?.critiques_count ?? '-'} />
	</div>

	<!-- Performance Summary -->
	<Card>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-6">
				{#if stats?.best_performing}
					<div>
						<span class="text-sm text-apple-text-tertiary">Best Performing:</span>
						<span class="ml-2 badge badge-success">{stats.best_performing}</span>
					</div>
				{/if}
				{#if stats?.worst_performing}
					<div>
						<span class="text-sm text-apple-text-tertiary">Needs Improvement:</span>
						<span class="ml-2 badge badge-danger">{stats.worst_performing}</span>
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

	<!-- Tab Navigation -->
	<div class="flex gap-1 border-b border-apple-border-subtle">
		{#each tabs as tab}
			<button
				class="tab"
				class:active={activeTab === tab.id}
				onclick={() => (activeTab = tab.id)}
			>
				{tab.label}
			</button>
		{/each}
	</div>

	<!-- Tab Content -->
	<Card>
		{#if loading}
			<div class="space-y-4">
				{#each Array(5) as _}
					<div class="skeleton h-16"></div>
				{/each}
			</div>
		{:else if activeTab === 'history'}
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
								<th class="table-header">Critique</th>
								<th class="table-header">Lesson</th>
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
									<td class="table-cell">
										{#if outcome.critique_generated}
											<span class="badge badge-info">Yes</span>
										{:else}
											<span class="text-apple-text-quaternary">-</span>
										{/if}
									</td>
									<td class="table-cell">
										{#if outcome.lesson_created}
											<span class="badge badge-success">Yes</span>
										{:else}
											<span class="text-apple-text-quaternary">-</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center py-12 text-center">
					<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
						<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
						</svg>
					</div>
					<p class="text-apple-text-secondary font-medium">No learning history available</p>
					<p class="text-sm text-apple-text-tertiary mt-1">Learning outcomes will appear here as the agent learns</p>
				</div>
			{/if}
		{:else if activeTab === 'critiques'}
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
							<div class="mt-3 text-right">
								<span class="font-mono {getConfidenceColor(critique.confidence)}">
									{(critique.confidence * 100).toFixed(0)}% confidence
								</span>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center py-12 text-center">
					<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
						<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
						</svg>
					</div>
					<p class="text-apple-text-secondary font-medium">No critiques available</p>
					<p class="text-sm text-apple-text-tertiary mt-1">Self-critiques will appear here when the agent reflects on failures</p>
				</div>
			{/if}
		{:else if activeTab === 'suggestions'}
			{#if suggestions.length > 0}
				<div class="space-y-4">
					{#each suggestions as suggestion, i}
						<div class="p-4 bg-apple-bg-tertiary rounded-apple-md border-l-2 border-l-apple-blue transition-all duration-150 hover:bg-apple-bg-elevated">
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Pattern Detected</p>
									<p class="text-apple-text-primary font-medium mt-1">{suggestion.pattern}</p>
									<p class="text-sm text-apple-text-secondary mt-2">{suggestion.suggestion}</p>
									{#if suggestion.affected_actions.length > 0}
										<div class="mt-3">
											<span class="text-xs text-apple-text-tertiary uppercase tracking-wider">Affected actions:</span>
											<div class="flex gap-1.5 mt-2 flex-wrap">
												{#each suggestion.affected_actions as action}
													<span class="badge badge-info text-xs">{action}</span>
												{/each}
											</div>
										</div>
									{/if}
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
					<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
						<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
						</svg>
					</div>
					<p class="text-apple-text-secondary font-medium">No improvement suggestions available</p>
					<p class="text-sm text-apple-text-tertiary mt-1 mb-4">Analyze failures to generate improvement suggestions</p>
					<button class="btn btn-secondary" onclick={analyzeFailures} disabled={analyzing}>
						{analyzing ? 'Analyzing...' : 'Analyze Recent Failures'}
					</button>
				</div>
			{/if}
		{/if}
	</Card>
</div>

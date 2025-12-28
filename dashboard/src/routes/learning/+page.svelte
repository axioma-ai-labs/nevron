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
		return success ? 'text-green-400' : 'text-red-400';
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'text-green-400';
		if (confidence >= 0.5) return 'text-yellow-400';
		return 'text-red-400';
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
						<span class="text-sm text-slate-400">Best Performing:</span>
						<span class="ml-2 badge badge-success">{stats.best_performing}</span>
					</div>
				{/if}
				{#if stats?.worst_performing}
					<div>
						<span class="text-sm text-slate-400">Needs Improvement:</span>
						<span class="ml-2 badge badge-danger">{stats.worst_performing}</span>
					</div>
				{/if}
			</div>
			<button class="btn btn-secondary" onclick={analyzeFailures} disabled={analyzing}>
				{analyzing ? 'Analyzing...' : 'Analyze Failures'}
			</button>
		</div>
	</Card>

	<!-- Tab Navigation -->
	<div class="flex gap-2 border-b border-surface-700">
		{#each tabs as tab}
			<button
				class="px-4 py-2 text-sm font-medium transition-colors
					{activeTab === tab.id
					? 'text-accent-400 border-b-2 border-accent-400'
					: 'text-slate-400 hover:text-white'}"
				onclick={() => (activeTab = tab.id)}
			>
				{tab.label}
			</button>
		{/each}
	</div>

	<!-- Tab Content -->
	<Card>
		{#if loading}
			<div class="animate-pulse space-y-4">
				{#each Array(5) as _}
					<div class="h-16 bg-surface-700 rounded"></div>
				{/each}
			</div>
		{:else if activeTab === 'history'}
			{#if history.length > 0}
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead>
							<tr class="text-left border-b border-surface-700">
								<th class="pb-3 text-sm text-slate-400 font-medium">Time</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Action</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Result</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Reward</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Success Rate</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Critique</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Lesson</th>
							</tr>
						</thead>
						<tbody>
							{#each history as outcome (outcome.timestamp)}
								<tr class="border-b border-surface-800">
									<td class="py-3 text-sm text-slate-400">{formatTime(outcome.timestamp)}</td>
									<td class="py-3 font-medium text-white">{outcome.action}</td>
									<td class="py-3">
										<span class={getSuccessColor(outcome.success)}>
											{outcome.success ? 'Success' : 'Failed'}
										</span>
									</td>
									<td class="py-3">
										<span class={outcome.reward >= 0 ? 'text-green-400' : 'text-red-400'}>
											{outcome.reward >= 0 ? '+' : ''}{outcome.reward.toFixed(2)}
										</span>
									</td>
									<td class="py-3 text-slate-300">
										{(outcome.new_success_rate * 100).toFixed(1)}%
									</td>
									<td class="py-3">
										{#if outcome.critique_generated}
											<span class="badge badge-info">Yes</span>
										{:else}
											<span class="text-slate-500">-</span>
										{/if}
									</td>
									<td class="py-3">
										{#if outcome.lesson_created}
											<span class="badge badge-success">Yes</span>
										{:else}
											<span class="text-slate-500">-</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="text-slate-500 text-center py-8">No learning history available</p>
			{/if}
		{:else if activeTab === 'critiques'}
			{#if critiques.length > 0}
				<div class="space-y-4">
					{#each critiques as critique (critique.timestamp)}
						<div class="p-4 bg-surface-800 rounded-lg border-l-2 border-yellow-500">
							<div class="flex items-center justify-between mb-2">
								<span class="badge badge-warning">{critique.action}</span>
								<span class="text-sm text-slate-500">{formatTime(critique.timestamp)}</span>
							</div>
							<div class="space-y-2">
								<div>
									<p class="text-xs text-slate-500 uppercase">What went wrong</p>
									<p class="text-slate-300">{critique.what_went_wrong}</p>
								</div>
								<div>
									<p class="text-xs text-slate-500 uppercase">Better approach</p>
									<p class="text-slate-300">{critique.better_approach}</p>
								</div>
								<div>
									<p class="text-xs text-slate-500 uppercase">Lesson learned</p>
									<p class="text-white font-medium">{critique.lesson_learned}</p>
								</div>
							</div>
							<div class="mt-2 text-right">
								<span class={getConfidenceColor(critique.confidence)}>
									{(critique.confidence * 100).toFixed(0)}% confidence
								</span>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-slate-500 text-center py-8">No critiques available</p>
			{/if}
		{:else if activeTab === 'suggestions'}
			{#if suggestions.length > 0}
				<div class="space-y-4">
					{#each suggestions as suggestion, i}
						<div class="p-4 bg-surface-800 rounded-lg border-l-2 border-accent-500">
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<p class="text-xs text-slate-500 uppercase">Pattern Detected</p>
									<p class="text-white font-medium">{suggestion.pattern}</p>
									<p class="text-sm text-slate-300 mt-2">{suggestion.suggestion}</p>
									{#if suggestion.affected_actions.length > 0}
										<div class="mt-2">
											<span class="text-xs text-slate-500">Affected actions:</span>
											<div class="flex gap-1 mt-1 flex-wrap">
												{#each suggestion.affected_actions as action}
													<span class="badge badge-info text-xs">{action}</span>
												{/each}
											</div>
										</div>
									{/if}
								</div>
								<span class={getConfidenceColor(suggestion.confidence)}>
									{(suggestion.confidence * 100).toFixed(0)}%
								</span>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-center py-8">
					<p class="text-slate-500">No improvement suggestions available</p>
					<button class="btn btn-secondary mt-4" onclick={analyzeFailures} disabled={analyzing}>
						Analyze Recent Failures
					</button>
				</div>
			{/if}
		{/if}
	</Card>
</div>

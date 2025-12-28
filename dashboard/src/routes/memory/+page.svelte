<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import StatCard from '$lib/components/StatCard.svelte';
	import {
		memoryAPI,
		type MemoryStatistics,
		type Episode,
		type Fact,
		type Concept,
		type Skill
	} from '$lib/api/client';

	let stats: MemoryStatistics | null = $state(null);
	let episodes: Episode[] = $state([]);
	let facts: Fact[] = $state([]);
	let concepts: Concept[] = $state([]);
	let skills: Skill[] = $state([]);
	let loading = $state(true);
	let consolidating = $state(false);
	let activeTab = $state('episodes');
	let searchQuery = $state('');
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
			const res = await memoryAPI.getStatistics();
			if (res.data) stats = res.data;
		} catch (e) {
			console.error('Failed to fetch memory stats:', e);
		}
	}

	async function fetchData() {
		loading = true;
		try {
			const [statsRes, episodesRes, factsRes, conceptsRes, skillsRes] = await Promise.all([
				memoryAPI.getStatistics(),
				memoryAPI.getEpisodes(50),
				memoryAPI.getFacts(50),
				memoryAPI.getConcepts(50),
				memoryAPI.getSkills(50)
			]);

			if (statsRes.data) stats = statsRes.data;
			if (episodesRes.data) episodes = episodesRes.data;
			if (factsRes.data) facts = factsRes.data;
			if (conceptsRes.data) concepts = conceptsRes.data;
			if (skillsRes.data) skills = skillsRes.data;
		} catch (e) {
			console.error('Failed to fetch memory data:', e);
		}
		loading = false;
	}

	async function search() {
		if (!searchQuery.trim()) return;
		loading = true;
		try {
			const res = await memoryAPI.recall(searchQuery, 20);
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

	async function consolidate() {
		consolidating = true;
		try {
			const res = await memoryAPI.consolidate();
			console.log('Consolidation result:', res.data);
			await fetchData();
		} catch (e) {
			console.error('Failed to consolidate memories:', e);
		}
		consolidating = false;
	}

	function formatTime(timestamp: string): string {
		return new Date(timestamp).toLocaleString();
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

	let tabs = $derived([
		{ id: 'episodes', label: 'Episodes', count: stats?.total_episodes ?? episodes.length },
		{ id: 'facts', label: 'Facts', count: stats?.total_facts ?? facts.length },
		{ id: 'concepts', label: 'Concepts', count: stats?.total_concepts ?? concepts.length },
		{ id: 'skills', label: 'Skills', count: stats?.total_skills ?? skills.length }
	]);
</script>

<div class="space-y-6">
	<!-- Stats Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
		<StatCard label="Episodes" value={stats?.total_episodes ?? '-'} icon="memory" />
		<StatCard label="Facts" value={stats?.total_facts ?? '-'} />
		<StatCard label="Concepts" value={stats?.total_concepts ?? '-'} />
		<StatCard label="Skills" value={stats?.total_skills ?? '-'} />
	</div>

	<!-- Search and Controls -->
	<Card>
		<div class="flex items-center gap-4">
			<div class="flex-1 flex gap-3">
				<input
					type="text"
					class="input flex-1"
					placeholder="Search memories..."
					bind:value={searchQuery}
					onkeydown={(e) => e.key === 'Enter' && search()}
				/>
				<button class="btn btn-primary" onclick={search}>
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
					<span class="badge {stats?.consolidation_running ? 'badge-warning' : 'badge-neutral'}">
						{stats?.consolidation_running ? 'Running' : 'Idle'}
					</span>
				</div>
				<button class="btn btn-secondary" onclick={consolidate} disabled={consolidating}>
					{consolidating ? 'Consolidating...' : 'Consolidate Now'}
				</button>
			</div>
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
				<span class="ml-1.5 text-xs text-apple-text-quaternary font-mono">({tab.count})</span>
			</button>
		{/each}
	</div>

	<!-- Tab Content -->
	<Card>
		{#if loading}
			<div class="space-y-4">
				{#each Array(5) as _}
					<div class="skeleton h-20"></div>
				{/each}
			</div>
		{:else if activeTab === 'episodes'}
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
					<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
						<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
						</svg>
					</div>
					<p class="text-apple-text-secondary font-medium">No episodes found</p>
				</div>
			{/if}
		{:else if activeTab === 'facts'}
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
		{:else if activeTab === 'concepts'}
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
		{:else if activeTab === 'skills'}
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
</div>

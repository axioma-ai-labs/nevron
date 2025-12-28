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
		if (importance >= 0.8) return 'text-red-400';
		if (importance >= 0.5) return 'text-yellow-400';
		return 'text-slate-400';
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'text-green-400';
		if (confidence >= 0.5) return 'text-yellow-400';
		return 'text-red-400';
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
			<div class="flex-1 flex gap-2">
				<input
					type="text"
					class="input flex-1"
					placeholder="Search memories..."
					bind:value={searchQuery}
					onkeydown={(e) => e.key === 'Enter' && search()}
				/>
				<button class="btn btn-primary" onclick={search}>Search</button>
				<button class="btn btn-secondary" onclick={fetchData}>Reset</button>
			</div>
			<div class="flex items-center gap-4">
				<div class="text-sm">
					<span class="text-slate-400">Consolidation:</span>
					<span class="badge {stats?.consolidation_running ? 'badge-warning' : 'badge-info'} ml-2">
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
				<span class="ml-1 text-xs text-slate-500">({tab.count})</span>
			</button>
		{/each}
	</div>

	<!-- Tab Content -->
	<Card>
		{#if loading}
			<div class="animate-pulse space-y-4">
				{#each Array(5) as _}
					<div class="h-20 bg-surface-700 rounded"></div>
				{/each}
			</div>
		{:else if activeTab === 'episodes'}
			{#if episodes.length > 0}
				<div class="space-y-4">
					{#each episodes as episode (episode.id)}
						<div class="p-4 bg-surface-800 rounded-lg">
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<p class="font-medium text-white">{episode.event}</p>
									<p class="text-sm text-slate-400 mt-1">
										<span class="font-medium">Action:</span>
										{episode.action}
									</p>
									<p class="text-sm text-slate-400">
										<span class="font-medium">Outcome:</span>
										{episode.outcome}
									</p>
								</div>
								<div class="text-right text-sm">
									<p class="text-slate-500">{formatTime(episode.timestamp)}</p>
									<p class={getImportanceColor(episode.importance)}>
										Importance: {(episode.importance * 100).toFixed(0)}%
									</p>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-slate-500 text-center py-8">No episodes found</p>
			{/if}
		{:else if activeTab === 'facts'}
			{#if facts.length > 0}
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead>
							<tr class="text-left border-b border-surface-700">
								<th class="pb-3 text-sm text-slate-400 font-medium">Subject</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Predicate</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Object</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Confidence</th>
								<th class="pb-3 text-sm text-slate-400 font-medium">Source</th>
							</tr>
						</thead>
						<tbody>
							{#each facts as fact (fact.id)}
								<tr class="border-b border-surface-800">
									<td class="py-3 font-medium text-white">{fact.subject}</td>
									<td class="py-3 text-slate-300">{fact.predicate}</td>
									<td class="py-3 text-slate-300">{fact.object}</td>
									<td class="py-3">
										<span class={getConfidenceColor(fact.confidence)}>
											{(fact.confidence * 100).toFixed(0)}%
										</span>
									</td>
									<td class="py-3 text-sm text-slate-500">{fact.source}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="text-slate-500 text-center py-8">No facts found</p>
			{/if}
		{:else if activeTab === 'concepts'}
			{#if concepts.length > 0}
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					{#each concepts as concept (concept.id)}
						<div class="p-4 bg-surface-800 rounded-lg">
							<div class="flex items-center gap-2 mb-2">
								<span class="font-medium text-white">{concept.name}</span>
								<span class="badge badge-info">{concept.concept_type}</span>
							</div>
							<p class="text-sm text-slate-400">{concept.description}</p>
							<p class="text-xs text-slate-500 mt-2">{formatTime(concept.created_at)}</p>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-slate-500 text-center py-8">No concepts found</p>
			{/if}
		{:else if activeTab === 'skills'}
			{#if skills.length > 0}
				<div class="space-y-4">
					{#each skills as skill (skill.id)}
						<div class="p-4 bg-surface-800 rounded-lg">
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<p class="font-medium text-white">{skill.name}</p>
									<p class="text-sm text-slate-400 mt-1">{skill.description}</p>
									<p class="text-sm text-slate-400 mt-1">
										<span class="font-medium">Trigger:</span>
										{skill.trigger_pattern}
									</p>
									{#if skill.action_sequence.length > 0}
										<div class="mt-2">
											<span class="text-xs text-slate-500">Actions:</span>
											<div class="flex gap-1 mt-1 flex-wrap">
												{#each skill.action_sequence as action}
													<span class="badge badge-info text-xs">{action}</span>
												{/each}
											</div>
										</div>
									{/if}
								</div>
								<div class="text-right text-sm">
									<p class={getConfidenceColor(skill.confidence)}>
										{(skill.confidence * 100).toFixed(0)}% confident
									</p>
									<p class="text-slate-500">
										{skill.success_count}/{skill.execution_count} success
									</p>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-slate-500 text-center py-8">No skills found</p>
			{/if}
		{/if}
	</Card>
</div>

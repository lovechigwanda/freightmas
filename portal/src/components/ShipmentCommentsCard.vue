<template>
	<div class="sd-card">
		<div class="sd-card-title">
			<span class="sd-card-title-main">
				<span class="sd-card-title-icon"><History /></span>
				Recent Tracking Comments
			</span>
		</div>
		<ul v-if="updates?.length" class="sd-list sd-comments-list">
			<li v-for="(item, idx) in updates" :key="idx">
				<div class="sd-comments-meta">
					<strong>{{ item.source || "Update" }}</strong>
					<span class="sd-muted">{{ formatDateTime(item.date) }}</span>
				</div>
				<div class="sd-comments-body">{{ item.event }}</div>
			</li>
		</ul>
		<EmptyState v-else :icon="Clock" title="No tracking updates yet" />
	</div>
</template>

<script setup>
import { Clock, History } from "@lucide/vue";
import { formatDateTime } from "../format";
import EmptyState from "./EmptyState.vue";

defineProps({
	updates: { type: Array, default: () => [] },
});
</script>

<template>
	<div class="sd-card sd-tracking-banner" :class="`sd-tracking-banner--${banner.status_key}`">
		<div class="sd-tracking-banner-top">
			<span class="sd-tracking-status-chip">{{ banner.status_label }}</span>
			<span v-if="banner.operational_phase_label" class="sd-tracking-phase">{{ banner.operational_phase_label }}</span>
			<span class="sd-tracking-progress">
				<ProgressBar :percent="banner.progress_percent" />
			</span>
		</div>
		<div v-if="banner.latest_update" class="sd-tracking-latest">{{ banner.latest_update }}</div>
		<div v-if="banner.key_date" class="sd-tracking-key-date">
			<span class="sd-muted">{{ banner.key_date_label }}</span>
			<span>{{ formatDate(banner.key_date) }}</span>
		</div>
	</div>
</template>

<script setup>
import { formatDate } from "../format";
import ProgressBar from "./ProgressBar.vue";

defineProps({
	banner: { type: Object, required: true },
});
</script>

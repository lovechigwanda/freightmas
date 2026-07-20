<template>
	<ul class="sd-timeline">
		<li v-for="(item, idx) in items" :key="idx" class="sd-timeline-item">
			<span class="sd-timeline-marker">
				<span class="sd-timeline-dot" :class="item.done ? 'done' : 'pending'">
					<Check v-if="item.done" :size="10" stroke-width="3" />
				</span>
				<span v-if="idx < items.length - 1" class="sd-timeline-line"></span>
			</span>
			<span class="sd-timeline-content">
				<span class="sd-timeline-label">{{ item.label }}</span>
				<span v-if="item.sub" class="sd-timeline-sub">{{ item.sub }}</span>
			</span>
			<span class="sd-timeline-date">
				{{ item.date ? formatDate(item.date) : item.next ? "Pending (next)" : "Pending" }}
			</span>
		</li>
	</ul>
</template>

<script setup>
import { Check } from "@lucide/vue";
import { formatDate } from "../format";

defineProps({
	items: { type: Array, required: true },
});
</script>

<template>
	<div class="sd-card sd-dashboard-headline">
		<p v-if="fullName" class="sd-dashboard-headline-greeting">Welcome back, {{ fullName }}.</p>
		<p v-if="hasPulse" class="sd-dashboard-headline-text">
			<template v-if="attentionCount">
				<strong class="sd-dashboard-headline-warn">{{ formatNumber(attentionCount) }}</strong>
				{{ attentionCount === 1 ? "item needs" : "items need" }} your attention
			</template>
			<template v-if="attentionCount && overdueAmount">
				<span class="sd-dashboard-headline-sep">·</span>
			</template>
			<template v-if="overdueAmount">
				<strong>{{ formatMoney(overdueAmount) }}</strong> overdue
			</template>
		</p>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { formatMoney, formatNumber } from "../format";

const props = defineProps({
	attentionCount: { type: Number, default: 0 },
	overdueAmount: { type: Number, default: 0 },
	fullName: { type: String, default: "" },
});

const hasPulse = computed(() => props.attentionCount > 0 || props.overdueAmount > 0);
</script>

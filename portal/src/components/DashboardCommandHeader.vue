<template>
	<div class="sd-card sd-dashboard-headline">
		<p class="sd-dashboard-headline-text">
			<strong>{{ formatNumber(activeCount) }}</strong> active shipment(s)
			<template v-if="delayedCount">
				<span class="sd-dashboard-headline-sep">·</span>
				<strong class="sd-dashboard-headline-warn">{{ formatNumber(delayedCount) }}</strong> need attention
			</template>
			<template v-if="outstandingAmount">
				<span class="sd-dashboard-headline-sep">·</span>
				<strong>{{ formatMoney(outstandingAmount) }}</strong> outstanding
			</template>
		</p>
		<p v-if="fullName" class="sd-muted sd-dashboard-headline-greeting">Welcome back, {{ fullName }}.</p>
	</div>
</template>

<script setup>
import { formatMoney, formatNumber } from "../format";

defineProps({
	activeCount: { type: Number, default: 0 },
	delayedCount: { type: Number, default: 0 },
	outstandingAmount: { type: Number, default: 0 },
	fullName: { type: String, default: "" },
});
</script>

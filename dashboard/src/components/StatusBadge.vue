<template>
	<span class="sd-badge" :class="badgeClass">{{ status }}</span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	status: { type: String, default: "" },
});

const MAP = {
	Draft: "sd-badge-gray",
	"In Progress": "sd-badge-blue",
	Delivered: "sd-badge-green",
	Completed: "sd-badge-green",
	Closed: "sd-badge-gray",
	Cancelled: "sd-badge-red",
	Overdue: "sd-badge-red",
	Unpaid: "sd-badge-amber",
	Paid: "sd-badge-green",
};

const badgeClass = computed(() => MAP[props.status] || "sd-badge-gray");
</script>

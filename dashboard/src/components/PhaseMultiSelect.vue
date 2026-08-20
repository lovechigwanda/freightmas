<template>
	<div class="pmd-wrap" ref="rootEl">
		<button type="button" class="pmd-trigger" @click="toggle">
			<span>{{ label }}</span>
			<ChevronDown :size="14" stroke-width="2" />
		</button>

		<div v-if="open" class="pmd-panel">
			<div class="pmd-actions">
				<button type="button" class="pmd-link" @click="clearAll">Clear</button>
			</div>

			<div class="pmd-list">
				<label v-for="phase in options" :key="phase.value" class="pmd-item">
					<input type="checkbox" :value="phase.value" v-model="selected" />
					<span>{{ phase.label }}</span>
				</label>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { ChevronDown } from "@lucide/vue";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	options: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue", "change"]);

const open = ref(false);
const rootEl = ref(null);

const selected = computed({
	get: () => props.modelValue,
	set: (value) => {
		emit("update:modelValue", value);
		emit("change", value);
	},
});

const optionByValue = computed(() => {
	const map = new Map();
	for (const option of props.options) {
		map.set(option.value, option.label);
	}
	return map;
});

const label = computed(() => {
	if (!selected.value.length) return "All Phases";
	if (selected.value.length === 1) {
		return optionByValue.value.get(selected.value[0]) || "1 Phase";
	}
	return `${selected.value.length} Phases`;
});

function toggle() {
	open.value = !open.value;
}

function clearAll() {
	selected.value = [];
}

function onClickOutside(e) {
	if (rootEl.value && !rootEl.value.contains(e.target)) {
		open.value = false;
	}
}

onMounted(() => document.addEventListener("click", onClickOutside));
onBeforeUnmount(() => document.removeEventListener("click", onClickOutside));
</script>

<style scoped>
.pmd-wrap {
	position: relative;
	display: inline-block;
}

.pmd-trigger {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 8px 12px;
	border: 1px solid var(--sd-border);
	border-radius: var(--sd-radius-sm);
	background: var(--sd-surface);
	color: var(--sd-text);
	font-size: 13px;
	font-family: inherit;
	cursor: pointer;
	min-width: 140px;
	justify-content: space-between;
}

.pmd-trigger:hover {
	border-color: var(--sd-accent);
}

.pmd-panel {
	position: absolute;
	top: calc(100% + 6px);
	left: 0;
	z-index: 30;
	width: 240px;
	background: var(--sd-surface);
	border: 1px solid var(--sd-border);
	border-radius: var(--sd-radius);
	box-shadow: var(--sd-shadow-lg);
	padding: 10px;
}

.pmd-actions {
	display: flex;
	gap: 12px;
	margin-bottom: 8px;
}

.pmd-link {
	background: none;
	border: none;
	padding: 0;
	font-size: 12px;
	font-weight: 600;
	color: var(--sd-accent);
	cursor: pointer;
}

.pmd-list {
	max-height: 280px;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.pmd-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 8px;
	border-radius: var(--sd-radius-sm);
	font-size: 13px;
	color: var(--sd-text);
	cursor: pointer;
}

.pmd-item span {
	color: var(--sd-text);
	flex: 1;
	min-width: 0;
}

.pmd-item input[type="checkbox"] {
	width: 14px;
	height: 14px;
	margin: 0;
	padding: 0;
	border: 1px solid var(--sd-border);
	border-radius: 3px;
	flex-shrink: 0;
	accent-color: var(--sd-accent);
}

.pmd-item:hover {
	background: var(--sd-surface-alt);
}
</style>

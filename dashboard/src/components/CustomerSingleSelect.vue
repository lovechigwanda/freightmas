<template>
	<div class="cfd-wrap" ref="rootEl">
		<button type="button" class="cfd-trigger" @click="toggle">
			<Users :size="14" stroke-width="2" />
			<span>{{ label }}</span>
			<ChevronDown :size="14" stroke-width="2" />
		</button>

		<div v-if="open" class="cfd-panel">
			<input v-model="query" type="text" placeholder="Search customers..." class="cfd-search" />

			<div class="cfd-list">
				<div v-if="loading" class="sd-muted" style="padding: 10px; font-size: 13px;">Loading...</div>
				<label v-for="c in filtered" :key="c.name" class="cfd-item">
					<input
						type="radio"
						name="tracking-customer"
						:value="c.name"
						:checked="c.name === modelValue"
						@change="select(c.name)"
					/>
					<span>{{ c.customer_name }}</span>
				</label>
				<div v-if="!loading && !filtered.length" class="sd-muted" style="padding: 10px; font-size: 13px;">
					No customers found
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { Users, ChevronDown } from "@lucide/vue";
import { api } from "../modules/forwarding/api";

// Single-select sibling of CustomerFilterDropdown: same cfd-* trigger/panel/
// list styling, but the value is one customer `name` (or null) instead of an
// array. There's no Select All / Clear (meaningless for one choice), and
// picking an item both sets the value and closes the panel in one step - a
// single-select has no persistent multi-pick session to keep open.
const props = defineProps({
	modelValue: { type: String, default: null },
});
const emit = defineEmits(["update:modelValue"]);

const open = ref(false);
const query = ref("");
const customers = ref([]);
const loading = ref(false);
const rootEl = ref(null);

const filtered = computed(() => {
	const q = query.value.trim().toLowerCase();
	if (!q) return customers.value;
	return customers.value.filter((c) => (c.customer_name || "").toLowerCase().includes(q));
});

const label = computed(() => {
	if (!props.modelValue) return "Select Customer";
	const match = customers.value.find((c) => c.name === props.modelValue);
	return match ? match.customer_name : props.modelValue;
});

async function toggle() {
	open.value = !open.value;
	if (open.value && !customers.value.length) {
		loading.value = true;
		try {
			customers.value = await api.getCustomers();
		} catch (e) {
			// Leave the list empty on failure - this is a secondary filter
			// control, not worth its own error banner (mirrors the multi-select).
		} finally {
			loading.value = false;
		}
	}
}

function select(name) {
	emit("update:modelValue", name);
	open.value = false;
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
.cfd-wrap {
	position: relative;
	display: inline-block;
}

.cfd-trigger {
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
}

.cfd-trigger:hover {
	border-color: var(--sd-accent);
}

.cfd-panel {
	position: absolute;
	top: calc(100% + 6px);
	left: 0;
	z-index: 30;
	width: 260px;
	background: var(--sd-surface);
	border: 1px solid var(--sd-border);
	border-radius: var(--sd-radius);
	box-shadow: var(--sd-shadow-lg);
	padding: 10px;
}

.cfd-search {
	width: 100%;
	padding: 7px 10px;
	border: 1px solid var(--sd-border);
	border-radius: var(--sd-radius-sm);
	font-size: 13px;
	font-family: inherit;
	margin-bottom: 8px;
}

.cfd-list {
	max-height: 220px;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.cfd-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 8px;
	border-radius: var(--sd-radius-sm);
	font-size: 13px;
	cursor: pointer;
}

.cfd-item:hover {
	background: var(--sd-surface-alt);
}
</style>

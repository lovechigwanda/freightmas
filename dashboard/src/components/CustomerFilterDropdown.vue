<template>
	<div class="cfd-wrap" ref="rootEl">
		<button type="button" class="cfd-trigger" @click="toggle">
			<Users :size="14" stroke-width="2" />
			<span>{{ label }}</span>
			<ChevronDown :size="14" stroke-width="2" />
		</button>

		<div v-if="open" class="cfd-panel">
			<input v-model="query" type="text" placeholder="Search customers..." class="cfd-search" />

			<div class="cfd-actions">
				<button type="button" class="cfd-link" @click="selectAll">Select All</button>
				<button type="button" class="cfd-link" @click="clearAll">Clear</button>
			</div>

			<div class="cfd-list">
				<div v-if="loading" class="sd-muted" style="padding: 10px; font-size: 13px;">Loading...</div>
				<label v-for="c in filtered" :key="c.name" class="cfd-item">
					<input type="checkbox" :value="c.name" v-model="selected" />
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

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue"]);

const open = ref(false);
const query = ref("");
const customers = ref([]);
const loading = ref(false);
const rootEl = ref(null);

// A writable computed over the prop, not a locally-mirrored ref kept in sync
// via a pair of watchers - two watchers each re-assigning a *new* array back
// and forth (parent -> local, local -> parent) never settle, since a fresh
// array reference always looks "changed" to Vue regardless of its contents,
// which froze the whole page in an infinite reactive loop. A single
// get/set computed has one source of truth (the parent's ref) and only
// ever writes on an actual user action, so there's nothing to ping-pong.
const selected = computed({
	get: () => props.modelValue,
	set: (v) => emit("update:modelValue", v),
});

const filtered = computed(() => {
	const q = query.value.trim().toLowerCase();
	if (!q) return customers.value;
	return customers.value.filter((c) => (c.customer_name || "").toLowerCase().includes(q));
});

const label = computed(() => {
	if (!selected.value.length) return "All Customers";
	if (selected.value.length === 1) {
		const match = customers.value.find((c) => c.name === selected.value[0]);
		return match ? match.customer_name : "1 Customer";
	}
	return `${selected.value.length} Customers`;
});

async function toggle() {
	open.value = !open.value;
	if (open.value && !customers.value.length) {
		loading.value = true;
		try {
			customers.value = await api.getCustomers();
		} catch (e) {
			// Leave the list empty on failure - the surrounding Shipments view
			// already surfaces load errors for the main table; this is a
			// secondary filter control, not worth its own error banner.
		} finally {
			loading.value = false;
		}
	}
}

function selectAll() {
	selected.value = filtered.value.map((c) => c.name);
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

.cfd-actions {
	display: flex;
	gap: 12px;
	margin-bottom: 8px;
}

.cfd-link {
	background: none;
	border: none;
	padding: 0;
	font-size: 12px;
	font-weight: 600;
	color: var(--sd-accent);
	cursor: pointer;
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

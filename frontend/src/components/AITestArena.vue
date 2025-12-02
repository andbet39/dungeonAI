<template>
  <div class="ai-arena">
    <TabView v-model:activeIndex="activeTab">
      <!-- Profiles Tab -->
      <TabPanel header="Profiles">
        <div class="tab-content">
          <DataTable :value="profilesArray" :loading="loading" stripedRows size="small"
            tableStyle="min-width: 50rem">
            <Column field="name" header="Monster Type" sortable>
              <template #body="{ data }">
                <span v-tooltip="'Internal monster type identifier'">{{ data.name }}</span>
              </template>
            </Column>
            <Column field="aggression" header="Aggression">
              <template #body="{ data }">
                <span v-tooltip="'Higher = more likely to attack. Range 0-1'">
                  <ProgressBar :value="data.aggression * 100" :showValue="false" style="height: 8px" />
                </span>
              </template>
            </Column>
            <Column field="caution" header="Caution">
              <template #body="{ data }">
                <span v-tooltip="'Higher = more likely to flee when low HP. Range 0-1'">
                  <ProgressBar :value="data.caution * 100" :showValue="false" style="height: 8px" />
                </span>
              </template>
            </Column>
            <Column field="pack_mentality" header="Pack">
              <template #body="{ data }">
                <span v-tooltip="'Higher = prefers calling allies. Range 0-1'">
                  <ProgressBar :value="data.pack_mentality * 100" :showValue="false" style="height: 8px" />
                </span>
              </template>
            </Column>
            <Column field="cunning" header="Cunning">
              <template #body="{ data }">
                <span v-tooltip="'Higher = prefers ambush tactics. Range 0-1'">
                  <ProgressBar :value="data.cunning * 100" :showValue="false" style="height: 8px" />
                </span>
              </template>
            </Column>
            <Column field="learning_rate" header="Learn Rate">
              <template #body="{ data }">
                <span v-tooltip="'Q-learning alpha (α): How fast new experiences override old. Range 0-1'">
                  {{ data.learning_rate }}
                </span>
              </template>
            </Column>
            <Column field="exploration_rate" header="Explore %">
              <template #body="{ data }">
                <span v-tooltip="'Q-learning epsilon (ε): Probability of random action vs exploiting best known action'">
                  {{ (data.exploration_rate * 100).toFixed(1) }}%
                </span>
              </template>
            </Column>
          </DataTable>
        </div>
      </TabPanel>

      <!-- Knowledge Tab -->
      <TabPanel header="Knowledge">
        <div class="tab-content">
          <div class="knowledge-header">
            <Tag severity="info" v-tooltip="'Schema version determines Q-table compatibility. Changes reset all tables.'">
              Schema v{{ schemaVersion }}
            </Tag>
          </div>
          <DataTable :value="speciesArray" :loading="loading" stripedRows size="small">
            <Column field="name" header="Species" sortable>
              <template #body="{ data }">
                <span v-tooltip="'Monster species identifier'">{{ data.name }}</span>
              </template>
            </Column>
            <Column field="generation" header="Generation" sortable>
              <template #body="{ data }">
                <span v-tooltip="'Increments each time a monster of this species dies. Represents accumulated experience.'">
                  {{ data.generation }}
                </span>
              </template>
            </Column>
            <Column field="total_learning_steps" header="Learning Steps" sortable>
              <template #body="{ data }">
                <span v-tooltip="'Total Q-table updates. Each combat exchange triggers one update.'">
                  {{ data.total_learning_steps }}
                </span>
              </template>
            </Column>
            <Column field="q_table_shape" header="Q-Table Shape">
              <template #body="{ data }">
                <span v-tooltip="'[states × actions] - States encode HP/enemies/allies/room/distance combinations'">
                  {{ data.q_table_shape?.join(' × ') }}
                </span>
              </template>
            </Column>
            <Column field="q_table_nonzero" header="Non-zero" sortable>
              <template #body="{ data }">
                <span v-tooltip="'Q-table cells with learned values. Higher = more diverse experience.'">
                  {{ data.q_table_nonzero }}
                </span>
              </template>
            </Column>
            <Column field="q_table_mean" header="Q Mean">
              <template #body="{ data }">
                <span v-tooltip="'Average Q-value. Negative suggests taking more damage than dealing.'">
                  {{ data.q_table_mean?.toFixed(3) }}
                </span>
              </template>
            </Column>
            <Column field="q_table_max" header="Q Max">
              <template #body="{ data }">
                <span v-tooltip="'Highest Q-value. Represents best-known state-action pair.'">
                  {{ data.q_table_max?.toFixed(3) }}
                </span>
              </template>
            </Column>
            <Column field="history_count" header="History">
              <template #body="{ data }">
                <span v-tooltip="'Recent learning events stored for evolution tracking'">
                  {{ data.history_count || 0 }}
                </span>
              </template>
            </Column>
            <Column header="Actions">
              <template #body="{ data }">
                <Button icon="pi pi-chart-line" severity="info" size="small" text
                  @click="showEvolution(data.name)" v-tooltip="'View evolution history'" />
                <Button icon="pi pi-refresh" severity="danger" size="small" text
                  @click="resetSpecies(data.name)" v-tooltip="'Reset Q-table'" />
              </template>
            </Column>
          </DataTable>
        </div>
      </TabPanel>

      <!-- Monsters Tab -->
      <TabPanel header="Monsters">
        <div class="tab-content">
          <DataTable :value="monstersArray" :loading="loading" stripedRows size="small"
            v-model:expandedRows="expandedMonsterRows" dataKey="id">
            <Column expander style="width: 3rem" />
            <Column field="name" header="Name" sortable />
            <Column field="monster_type" header="Type" sortable />
            <Column field="hp" header="HP">
              <template #body="{ data }">
                <div class="hp-display">
                  <span v-tooltip="'Current / Maximum hit points'">{{ data.hp }}/{{ data.max_hp }}</span>
                  <ProgressBar :value="(data.hp / data.max_hp) * 100" :showValue="false" style="height: 6px; width: 60px" />
                </div>
              </template>
            </Column>
            <Column header="Position">
              <template #body="{ data }">
                <span v-tooltip="'X, Y coordinates on the dungeon map'">
                  ({{ data.position?.x }}, {{ data.position?.y }})
                </span>
              </template>
            </Column>
            <Column field="intelligence.generation" header="Gen" sortable>
              <template #body="{ data }">
                <span v-tooltip="'Species generation when this monster spawned'">
                  {{ data.intelligence?.generation }}
                </span>
              </template>
            </Column>
            <Column field="intelligence.last_action" header="Last Action">
              <template #body="{ data }">
                <Tag v-if="data.intelligence?.last_action" 
                  :value="data.intelligence.last_action" 
                  :severity="getActionSeverity(data.intelligence.last_action)"
                  v-tooltip="getActionTooltip(data.intelligence.last_action)" />
              </template>
            </Column>
            <template #expansion="{ data }">
              <div class="monster-expansion">
                <p><strong>State Index:</strong> <span v-tooltip="'Encoded state in Q-table (0 to state_space-1)'">{{ data.intelligence?.last_state_index ?? '—' }}</span></p>
                <p><strong>Last Reward:</strong> <span v-tooltip="'Reward from last action. Positive=good, Negative=bad'">{{ data.intelligence?.last_reward?.toFixed(2) }}</span></p>
                <p><strong>Memory Events:</strong> <span v-tooltip="'Threat events in short-term memory'">{{ data.memory_event_count }}</span></p>
                <p><strong>World State:</strong> {{ JSON.stringify(data.intelligence?.last_world_state) }}</p>
              </div>
            </template>
          </DataTable>
        </div>
      </TabPanel>

      <!-- Evolution Tab (replaced Simulate) -->
      <TabPanel header="Evolution">
        <div class="tab-content evolution-tab">
          <div class="evolution-controls">
            <Select v-model="evolutionSpecies" :options="speciesOptions" optionLabel="name" optionValue="name"
              placeholder="Select species" class="species-select" @change="loadEvolutionData" />
            <Button icon="pi pi-refresh" label="Refresh" severity="secondary" @click="loadEvolutionData" 
              :disabled="!evolutionSpecies" />
          </div>
          
          <div v-if="evolutionData" class="evolution-charts">
            <!-- Reward Chart -->
            <Card>
              <template #title>
                <span v-tooltip="'Rewards received over time. Positive = damage dealt, Negative = damage taken or death'">
                  Reward History
                </span>
              </template>
              <template #content>
                <Line v-if="rewardChartData.datasets[0].data.length" :data="rewardChartData" :options="rewardChartOptions" />
                <p v-else class="no-data">No learning history yet. Run the sandbox to generate data.</p>
              </template>
            </Card>
            
            <!-- Q-Value Evolution Chart -->
            <Card>
              <template #title>
                <span v-tooltip="'How Q-values change with each learning step. Shows learning progression.'">
                  Q-Value Changes
                </span>
              </template>
              <template #content>
                <Line v-if="qValueChartData.datasets[0].data.length" :data="qValueChartData" :options="qValueChartOptions" />
                <p v-else class="no-data">No Q-value history yet.</p>
              </template>
            </Card>
            
            <!-- Action Distribution Chart -->
            <Card>
              <template #title>
                <span v-tooltip="'Distribution of actions chosen during learning. Shows behavioral patterns.'">
                  Action Distribution
                </span>
              </template>
              <template #content>
                <Bar v-if="hasActionData" :data="actionChartData" :options="actionChartOptions" />
                <p v-else class="no-data">No action data yet.</p>
              </template>
            </Card>
            
            <!-- Summary Stats -->
            <Card>
              <template #title>Learning Summary</template>
              <template #content>
                <div class="summary-grid">
                  <div class="stat-box">
                    <span class="stat-label" v-tooltip="'Total learning updates recorded'">Total Events</span>
                    <span class="stat-value">{{ evolutionData.total }}</span>
                  </div>
                  <div class="stat-box">
                    <span class="stat-label" v-tooltip="'Sum of all rewards received'">Total Reward</span>
                    <span class="stat-value" :class="totalReward >= 0 ? 'positive' : 'negative'">
                      {{ totalReward.toFixed(1) }}
                    </span>
                  </div>
                  <div class="stat-box">
                    <span class="stat-label" v-tooltip="'Average reward per learning event'">Avg Reward</span>
                    <span class="stat-value" :class="avgReward >= 0 ? 'positive' : 'negative'">
                      {{ avgReward.toFixed(2) }}
                    </span>
                  </div>
                  <div class="stat-box">
                    <span class="stat-label" v-tooltip="'Average Q-value change magnitude'">Avg Q-Delta</span>
                    <span class="stat-value">{{ avgQDelta.toFixed(4) }}</span>
                  </div>
                </div>
              </template>
            </Card>
          </div>
          
          <div v-else class="evolution-placeholder">
            <i class="pi pi-chart-line" style="font-size: 3rem; opacity: 0.3"></i>
            <p>Select a species to view evolution data</p>
          </div>
        </div>
      </TabPanel>

      <!-- Sandbox Tab -->
      <TabPanel header="Sandbox">
        <div class="sandbox-tab">
          <Splitter style="height: calc(100vh - 180px)">
            <SplitterPanel :size="60" :minSize="40">
              <div class="sandbox-map-container">
                <Toolbar class="sandbox-toolbar">
                  <template #start>
                    <SelectButton v-model="sandboxMode" :options="sandboxModes" optionLabel="label" optionValue="value" />
                  </template>
                  <template #center>
                    <Select v-model="selectedMonsterType" :options="monsterTypes" optionLabel="name" optionValue="type"
                      placeholder="Monster type" class="monster-select" v-if="sandboxMode === 'spawn'" />
                  </template>
                  <template #end>
                    <Button icon="pi pi-refresh" label="Reset" severity="secondary" @click="resetSandbox" />
                  </template>
                </Toolbar>
                <div class="map-wrapper" ref="sandboxMapContainer" @click="handleMapClick" tabindex="0" @keydown="handleKeyDown">
                  <div id="sandbox-game" ref="sandboxCanvas"></div>
                </div>
                <div class="map-instructions">
                  <span v-if="sandboxMode === 'spawn'">Click on map to spawn {{ selectedMonsterType || 'monster' }}</span>
                  <span v-else-if="sandboxMode === 'threat'">Click on map to place threat</span>
                  <span v-else>Use arrow keys to move threat</span>
                </div>
              </div>
            </SplitterPanel>
            <SplitterPanel :size="40" :minSize="30">
              <div class="sandbox-panels">
                <!-- Simulation Controls -->
                <Panel header="Simulation" toggleable>
                  <div class="sim-controls">
                    <div class="control-row">
                      <Button :icon="sandboxState?.running ? 'pi pi-pause' : 'pi pi-play'"
                        :label="sandboxState?.running ? 'Pause' : 'Run'"
                        :severity="sandboxState?.running ? 'warning' : 'success'"
                        @click="toggleSandboxRun" 
                        v-tooltip.top="'Start/stop automatic tick progression'" />
                      <Button icon="pi pi-step-forward" label="Step" severity="secondary"
                        @click="stepSandbox" :disabled="sandboxState?.running"
                        v-tooltip.top="'Execute a single simulation tick'" />
                    </div>
                    <div class="control-row combat-toggle">
                      <ToggleSwitch v-model="sandboxCombatEnabled" @change="toggleSandboxCombat" />
                      <label v-tooltip.right="'Enable dice-based combat simulation. Monsters will attack the threat using real dice rolls (d20 attack, damage dice) when adjacent.'">
                        Combat Enabled
                      </label>
                    </div>
                    <div class="control-row">
                      <label>Speed (ms)</label>
                      <Slider v-model="sandboxSpeed" :min="100" :max="2000" :step="100" class="speed-slider" />
                      <span>{{ sandboxSpeed }}ms</span>
                    </div>
                    <div class="tick-display">
                      <Tag severity="secondary" v-tooltip.top="'Current simulation tick count'">Tick: {{ sandboxState?.tick || 0 }}</Tag>
                      <Tag v-if="sandboxState?.threat" :severity="sandboxState.threat.hp > 25 ? 'success' : 'danger'"
                        v-tooltip.top="'Threat HP (only shown when combat is enabled)'">
                        Threat HP: {{ sandboxState.threat.hp }}/{{ sandboxState.threat.max_hp }}
                      </Tag>
                    </div>
                  </div>
                </Panel>

                <!-- Active Monsters -->
                <Panel header="Monsters" toggleable>
                  <DataTable :value="sandboxMonstersArray" size="small" stripedRows scrollable scrollHeight="200px">
                    <Column field="name" header="Name" style="width: 30%" />
                    <Column header="HP" style="width: 35%">
                      <template #body="{ data }">
                        <div class="monster-hp-edit">
                          <InputNumber v-model="data.hp" :min="1" :max="data.max_hp" size="small"
                            @update:modelValue="setMonsterHP(data.id, $event)" inputStyle="width: 50px" />
                          <span>/{{ data.max_hp }}</span>
                        </div>
                      </template>
                    </Column>
                    <Column header="Pos" style="width: 20%">
                      <template #body="{ data }">({{ data.x }}, {{ data.y }})</template>
                    </Column>
                    <Column style="width: 15%">
                      <template #body="{ data }">
                        <Button icon="pi pi-trash" severity="danger" size="small" text
                          @click="removeMonster(data.id)" />
                      </template>
                    </Column>
                  </DataTable>
                  <Button v-if="sandboxState?.threat" icon="pi pi-times" label="Remove Threat"
                    severity="secondary" size="small" class="mt-2" @click="removeThreat" />
                </Panel>

                <!-- Decision Log -->
                <Panel header="Decision Log" toggleable class="decision-log-panel">
                  <DataTable :value="decisionLogArray" size="small" stripedRows scrollable scrollHeight="250px"
                    v-model:expandedRows="expandedLogRows" dataKey="tick">
                    <Column expander style="width: 3rem" />
                    <Column field="tick" header="Tick" style="width: 15%" sortable />
                    <Column field="monster_name" header="Monster" style="width: 25%" />
                    <Column field="action" header="Action" style="width: 25%">
                      <template #body="{ data }">
                        <Tag :value="data.action" :severity="getActionSeverity(data.action)" />
                      </template>
                    </Column>
                    <Column field="explored" header="Exp?" style="width: 15%">
                      <template #body="{ data }">
                        <i :class="data.explored ? 'pi pi-question-circle' : 'pi pi-check-circle'"
                          :style="{ color: data.explored ? '#f59e0b' : '#22c55e' }" />
                      </template>
                    </Column>
                    <template #expansion="{ data }">
                      <div class="log-expansion">
                        <div class="state-breakdown">
                          <h5>State Breakdown</h5>
                          <ul>
                            <li><strong>HP Ratio:</strong> {{ data.state_breakdown?.hp_ratio?.toFixed(2) }}</li>
                            <li><strong>Enemies:</strong> {{ data.state_breakdown?.nearby_enemies }}</li>
                            <li><strong>Allies:</strong> {{ data.state_breakdown?.nearby_allies }}</li>
                            <li><strong>Room:</strong> {{ data.state_breakdown?.room_type }}</li>
                            <li><strong>Dist to Threat:</strong> {{ data.state_breakdown?.distance_to_threat }}</li>
                          </ul>
                        </div>
                        <div class="q-values-table">
                          <h5>Q-Values</h5>
                          <DataTable :value="formatQValues(data.q_values)" size="small">
                            <Column field="action" header="Action" />
                            <Column field="value" header="Q">
                              <template #body="{ data: qv }">
                                <span :class="{ 'q-highlight': qv.isMax }">{{ qv.value.toFixed(4) }}</span>
                              </template>
                            </Column>
                          </DataTable>
                        </div>
                      </div>
                    </template>
                  </DataTable>
                </Panel>
              </div>
            </SplitterPanel>
          </Splitter>
        </div>
      </TabPanel>
    </TabView>

    <Button icon="pi pi-refresh" class="refresh-button" severity="secondary" rounded
      @click="refreshAll" :loading="loading" v-tooltip="'Refresh data'" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as ROT from 'rot-js'

// Chart.js
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  ChartTooltip,
  Legend,
  Filler
)

// PrimeVue components
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Panel from 'primevue/panel'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import Slider from 'primevue/slider'
import ProgressBar from 'primevue/progressbar'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import Toolbar from 'primevue/toolbar'
import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'
import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'

const API_BASE = '/api/admin'

// Tab state
const activeTab = ref(0)
const loading = ref(false)

// Data
const profiles = ref({})
const species = ref({})
const monsters = ref({})
const schemaVersion = ref(1)

// Evolution data
const evolutionSpecies = ref(null)
const evolutionData = ref(null)

// Action tooltips
const actionTooltips = {
  'ATTACK_AGGRESSIVE': 'Full attack with no defense consideration',
  'ATTACK_DEFENSIVE': 'Attack while maintaining defensive posture',
  'DEFEND': 'Focus on defense, no attack this turn',
  'FLEE': 'Attempt to escape combat',
  'CALL_ALLIES': 'Alert nearby allies for assistance',
  'AMBUSH': 'Wait for optimal attack opportunity',
  'PATROL': 'Standard patrol movement'
}

function getActionTooltip(action) {
  return actionTooltips[action] || 'Unknown action'
}

// Expanded rows
const expandedMonsterRows = ref([])
const expandedLogRows = ref([])

// Sandbox state
const sandboxState = ref(null)
const sandboxMode = ref('spawn')
const sandboxModes = [
  { label: 'Spawn Monster', value: 'spawn' },
  { label: 'Place Threat', value: 'threat' },
  { label: 'Move Threat', value: 'move' }
]
const selectedMonsterType = ref(null)
const monsterTypes = ref([])
const sandboxSpeed = ref(500)
const sandboxCombatEnabled = ref(true)
const sandboxCanvas = ref(null)
const sandboxMapContainer = ref(null)
let sandboxDisplay = null
let sandboxWs = null

// Tile constants
const TILE = {
  FLOOR: 0, WALL: 1, DOOR_CLOSED: 2, DOOR_OPEN: 3,
  CHEST: 4, TABLE: 5, CHAIR: 6, BED: 7,
  BOOKSHELF: 8, BARREL: 9, TORCH: 10, VOID: 11
}

// Computed arrays for DataTable
const profilesArray = computed(() => {
  return Object.entries(profiles.value).map(([name, p]) => ({
    name,
    aggression: p.personality?.aggression || 0,
    caution: p.personality?.caution || 0,
    pack_mentality: p.personality?.pack_mentality || 0,
    cunning: p.personality?.cunning || 0,
    learning_rate: p.learning_rate,
    exploration_rate: p.exploration_rate
  }))
})

const speciesArray = computed(() => {
  return Object.entries(species.value).map(([name, s]) => ({ name, ...s }))
})

const speciesOptions = computed(() => {
  return speciesArray.value.map(s => ({ name: s.name }))
})

const monstersArray = computed(() => {
  return Object.entries(monsters.value).map(([id, m]) => ({ id, ...m }))
})

const sandboxMonstersArray = computed(() => {
  if (!sandboxState.value?.monsters) return []
  return Object.values(sandboxState.value.monsters)
})

const decisionLogArray = computed(() => {
  if (!sandboxState.value?.decision_log) return []
  return [...sandboxState.value.decision_log].reverse()
})

const combatLogArray = computed(() => {
  if (!sandboxState.value?.combat_log) return []
  return [...sandboxState.value.combat_log].reverse().slice(0, 20)
})

// Evolution chart data
const rewardChartData = computed(() => {
  if (!evolutionData.value?.history) return { labels: [], datasets: [{ data: [] }] }
  const history = evolutionData.value.history
  return {
    labels: history.map((_, i) => i + 1),
    datasets: [{
      label: 'Reward',
      data: history.map(h => h.reward),
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
      fill: true,
      tension: 0.1
    }]
  }
})

const qValueChartData = computed(() => {
  if (!evolutionData.value?.history) return { labels: [], datasets: [{ data: [] }] }
  const history = evolutionData.value.history
  return {
    labels: history.map((_, i) => i + 1),
    datasets: [
      {
        label: 'Q-Value Before',
        data: history.map(h => h.q_value_before),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        tension: 0.1
      },
      {
        label: 'Q-Value After',
        data: history.map(h => h.q_value_after),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        tension: 0.1
      }
    ]
  }
})

const actionChartData = computed(() => {
  if (!evolutionData.value?.history) return { labels: [], datasets: [{ data: [] }] }
  const actionCounts = {}
  for (const h of evolutionData.value.history) {
    actionCounts[h.action] = (actionCounts[h.action] || 0) + 1
  }
  const labels = Object.keys(actionCounts)
  const data = Object.values(actionCounts)
  const colors = labels.map(action => {
    const colorMap = {
      'ATTACK_AGGRESSIVE': 'rgba(239, 68, 68, 0.8)',
      'ATTACK_DEFENSIVE': 'rgba(249, 115, 22, 0.8)',
      'DEFEND': 'rgba(34, 197, 94, 0.8)',
      'FLEE': 'rgba(168, 162, 158, 0.8)',
      'CALL_ALLIES': 'rgba(59, 130, 246, 0.8)',
      'AMBUSH': 'rgba(139, 92, 246, 0.8)',
      'PATROL': 'rgba(107, 114, 128, 0.8)'
    }
    return colorMap[action] || 'rgba(100, 100, 100, 0.8)'
  })
  return {
    labels,
    datasets: [{
      label: 'Action Count',
      data,
      backgroundColor: colors
    }]
  }
})

const hasActionData = computed(() => {
  return evolutionData.value?.history?.length > 0
})

const totalReward = computed(() => {
  if (!evolutionData.value?.history) return 0
  return evolutionData.value.history.reduce((sum, h) => sum + h.reward, 0)
})

const avgReward = computed(() => {
  if (!evolutionData.value?.history?.length) return 0
  return totalReward.value / evolutionData.value.history.length
})

const avgQDelta = computed(() => {
  if (!evolutionData.value?.history?.length) return 0
  const deltas = evolutionData.value.history.map(h => Math.abs(h.q_delta || 0))
  return deltas.reduce((sum, d) => sum + d, 0) / deltas.length
})

const rewardChartOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' },
    tooltip: {
      callbacks: {
        label: (ctx) => `Reward: ${ctx.parsed.y.toFixed(2)}`
      }
    }
  },
  scales: {
    y: { title: { display: true, text: 'Reward' } },
    x: { title: { display: true, text: 'Learning Step' } }
  }
}

const qValueChartOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' }
  },
  scales: {
    y: { title: { display: true, text: 'Q-Value' } },
    x: { title: { display: true, text: 'Learning Step' } }
  }
}

const actionChartOptions = {
  responsive: true,
  plugins: {
    legend: { display: false }
  },
  scales: {
    y: { title: { display: true, text: 'Count' } }
  }
}

// API methods
async function fetchProfiles() {
  const res = await fetch(`${API_BASE}/ai/profiles`)
  const data = await res.json()
  profiles.value = data.profiles || {}
}

async function fetchSpecies() {
  const res = await fetch(`${API_BASE}/ai/species-knowledge`)
  const data = await res.json()
  species.value = data.species || {}
  schemaVersion.value = data.schema_version || 1
}

async function fetchMonsters() {
  const res = await fetch(`${API_BASE}/ai/monsters`)
  const data = await res.json()
  monsters.value = data.monsters || {}
}

async function fetchMonsterTypes() {
  const res = await fetch(`${API_BASE}/sandbox/monster-types`)
  const data = await res.json()
  monsterTypes.value = data.types || []
  if (monsterTypes.value.length && !selectedMonsterType.value) {
    selectedMonsterType.value = monsterTypes.value[0].type
  }
}

async function fetchSandboxState() {
  const res = await fetch(`${API_BASE}/sandbox/state`)
  sandboxState.value = await res.json()
  sandboxCombatEnabled.value = sandboxState.value?.combat_enabled ?? true
  renderSandbox()
}

async function loadEvolutionData() {
  if (!evolutionSpecies.value) return
  const res = await fetch(`${API_BASE}/ai/species-history/${evolutionSpecies.value}?limit=100`)
  evolutionData.value = await res.json()
}

function showEvolution(speciesName) {
  evolutionSpecies.value = speciesName
  activeTab.value = 3 // Evolution tab
  loadEvolutionData()
}

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([fetchProfiles(), fetchSpecies(), fetchMonsters(), fetchMonsterTypes(), fetchSandboxState()])
  } finally {
    loading.value = false
  }
}

async function resetSpecies(name) {
  if (!confirm(`Reset Q-table for ${name}?`)) return
  await fetch(`${API_BASE}/ai/reset-species/${name}`, { method: 'POST' })
  await fetchSpecies()
}

// Sandbox methods
async function resetSandbox() {
  await fetch(`${API_BASE}/sandbox/create`, { method: 'POST' })
  await fetchSandboxState()
}

async function stepSandbox() {
  const res = await fetch(`${API_BASE}/sandbox/step`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ count: 1 })
  })
  const data = await res.json()
  await fetchSandboxState()
}

async function toggleSandboxRun() {
  const running = !sandboxState.value?.running
  await fetch(`${API_BASE}/sandbox/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ running, speed_ms: sandboxSpeed.value })
  })
  sandboxState.value.running = running
}

async function toggleSandboxCombat() {
  await fetch(`${API_BASE}/sandbox/toggle-combat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ combat_enabled: sandboxCombatEnabled.value })
  })
}

async function setMonsterHP(monsterId, hp) {
  await fetch(`${API_BASE}/sandbox/set-hp/${monsterId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hp })
  })
}

async function removeMonster(monsterId) {
  await fetch(`${API_BASE}/sandbox/monster/${monsterId}`, { method: 'DELETE' })
  await fetchSandboxState()
}

async function removeThreat() {
  await fetch(`${API_BASE}/sandbox/threat`, { method: 'DELETE' })
  await fetchSandboxState()
}

function handleMapClick(event) {
  if (!sandboxDisplay || !sandboxState.value) return
  
  const rect = sandboxCanvas.value?.getBoundingClientRect()
  if (!rect) return
  
  const container = sandboxDisplay.getContainer()
  const cellWidth = container.offsetWidth / sandboxState.value.width
  const cellHeight = container.offsetHeight / sandboxState.value.height
  
  const x = Math.floor((event.clientX - rect.left) / cellWidth)
  const y = Math.floor((event.clientY - rect.top) / cellHeight)
  
  if (x < 0 || x >= sandboxState.value.width || y < 0 || y >= sandboxState.value.height) return
  
  if (sandboxMode.value === 'spawn' && selectedMonsterType.value) {
    spawnMonster(x, y)
  } else if (sandboxMode.value === 'threat') {
    placeThreat(x, y)
  }
}

async function spawnMonster(x, y) {
  await fetch(`${API_BASE}/sandbox/spawn-monster`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ monster_type: selectedMonsterType.value, x, y })
  })
  await fetchSandboxState()
}

async function placeThreat(x, y) {
  await fetch(`${API_BASE}/sandbox/spawn-threat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ x, y })
  })
  await fetchSandboxState()
}

function handleKeyDown(event) {
  if (sandboxMode.value !== 'move' || !sandboxState.value?.threat) return
  
  const keyMap = {
    'ArrowUp': 'up', 'ArrowDown': 'down',
    'ArrowLeft': 'left', 'ArrowRight': 'right'
  }
  
  const direction = keyMap[event.key]
  if (direction) {
    event.preventDefault()
    moveThreat(direction)
  }
}

async function moveThreat(direction) {
  await fetch(`${API_BASE}/sandbox/move-threat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ direction })
  })
  await fetchSandboxState()
}

// Sandbox rendering
function setupSandboxDisplay() {
  if (!sandboxState.value || !sandboxCanvas.value) return
  
  if (sandboxDisplay) {
    const old = sandboxDisplay.getContainer()
    if (old?.parentNode) old.parentNode.removeChild(old)
  }
  
  sandboxDisplay = new ROT.Display({
    width: sandboxState.value.width,
    height: sandboxState.value.height,
    fontSize: 20,
    fontFamily: 'monospace',
    bg: '#000',
    fg: '#fff'
  })
  
  sandboxCanvas.value.appendChild(sandboxDisplay.getContainer())
  renderSandbox()
}

function renderSandbox() {
  if (!sandboxDisplay || !sandboxState.value) return
  
  sandboxDisplay.clear()
  
  // Render tiles
  const tiles = sandboxState.value.tiles
  for (let y = 0; y < tiles.length; y++) {
    for (let x = 0; x < tiles[y].length; x++) {
      drawTile(x, y, tiles[y][x])
    }
  }
  
  // Render monsters
  for (const monster of Object.values(sandboxState.value.monsters || {})) {
    sandboxDisplay.draw(monster.x, monster.y, monster.symbol, monster.color, '#000')
  }
  
  // Render threat
  if (sandboxState.value.threat) {
    const t = sandboxState.value.threat
    sandboxDisplay.draw(t.x, t.y, t.symbol, t.color, '#000')
  }
}

function drawTile(x, y, tile) {
  switch (tile) {
    case TILE.VOID:
      sandboxDisplay.draw(x, y, ' ', '#000', '#000')
      break
    case TILE.WALL:
      sandboxDisplay.draw(x, y, '#', '#888', '#333')
      break
    case TILE.DOOR_CLOSED:
      sandboxDisplay.draw(x, y, '+', '#a52', '#321')
      break
    case TILE.DOOR_OPEN:
      sandboxDisplay.draw(x, y, '/', '#a52', '#000')
      break
    default:
      sandboxDisplay.draw(x, y, '.', '#555', '#000')
  }
}

function getActionSeverity(action) {
  const map = {
    'ATTACK_AGGRESSIVE': 'danger',
    'ATTACK_DEFENSIVE': 'warn',
    'FLEE': 'secondary',
    'PATROL': 'info',
    'AMBUSH': 'warn',
    'CALL_ALLIES': 'success'
  }
  return map[action] || 'info'
}

function formatQValues(qValues) {
  if (!qValues) return []
  const entries = Object.entries(qValues).map(([action, value]) => ({ action, value }))
  const maxValue = Math.max(...entries.map(e => e.value))
  return entries.map(e => ({ ...e, isMax: e.value === maxValue && maxValue !== 0 }))
}

// WebSocket for real-time sandbox updates
let wsReconnectTimeout = null
let lastRenderTime = 0
const MIN_RENDER_INTERVAL = 50 // ms - throttle rendering to max 20fps

function connectSandboxWs() {
  if (wsReconnectTimeout) {
    clearTimeout(wsReconnectTimeout)
    wsReconnectTimeout = null
  }
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  sandboxWs = new WebSocket(`${protocol}//${window.location.host}/ws/sandbox`)
  
  sandboxWs.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.type === 'sandbox_state') {
      // Full state - replace everything
      sandboxState.value = msg.state
      renderSandbox()
    } else if (msg.type === 'sandbox_update') {
      // Delta update - merge with existing state, preserving static data
      if (sandboxState.value) {
        sandboxState.value = {
          ...sandboxState.value,
          ...msg.state,
          // Preserve static data that's not in delta updates
          tiles: sandboxState.value.tiles,
          width: sandboxState.value.width,
          height: sandboxState.value.height,
          rooms: sandboxState.value.rooms,
        }
      } else {
        sandboxState.value = msg.state
      }
      
      // Throttle rendering to prevent performance issues
      const now = Date.now()
      if (now - lastRenderTime >= MIN_RENDER_INTERVAL) {
        lastRenderTime = now
        renderSandbox()
      }
    }
  }
  
  sandboxWs.onclose = () => {
    // Only reconnect if component is still mounted
    if (!wsReconnectTimeout) {
      wsReconnectTimeout = setTimeout(connectSandboxWs, 2000)
    }
  }
  
  sandboxWs.onerror = () => {
    // Close on error to trigger reconnect
    if (sandboxWs) sandboxWs.close()
  }
}

// Watch for speed changes
watch(sandboxSpeed, async (newSpeed) => {
  if (sandboxState.value?.running) {
    await fetch(`${API_BASE}/sandbox/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ running: true, speed_ms: newSpeed })
    })
  }
})

// Watch for tab changes to setup sandbox display
watch(activeTab, async (newTab) => {
  if (newTab === 4) { // Sandbox tab
    await nextTick()
    if (!sandboxDisplay) {
      await fetchSandboxState()
      setupSandboxDisplay()
    }
  }
})

onMounted(async () => {
  await refreshAll()
  connectSandboxWs()
})

onUnmounted(() => {
  // Clear reconnect timeout
  if (wsReconnectTimeout) {
    clearTimeout(wsReconnectTimeout)
    wsReconnectTimeout = null
  }
  
  // Close WebSocket
  if (sandboxWs) {
    sandboxWs.onclose = null // Prevent reconnect on intentional close
    sandboxWs.close()
    sandboxWs = null
  }
  
  // Cleanup ROT.Display
  if (sandboxDisplay) {
    const container = sandboxDisplay.getContainer()
    if (container?.parentNode) {
      container.parentNode.removeChild(container)
    }
    sandboxDisplay = null
  }
})
</script>

<style scoped>
.ai-arena {
  min-height: 100%;
  padding: 1rem;
  background: var(--p-surface-ground);
}

.ai-arena :deep(.p-tabview) {
  background: var(--p-surface-card);
  border-radius: 6px;
}

.ai-arena :deep(.p-tabview-panels) {
  padding: 0;
  background: var(--p-surface-card);
}

.tab-content {
  padding: 1rem;
}

.hp-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.monster-expansion {
  padding: 1rem;
  border-radius: 4px;
}

.monster-expansion p {
  margin: 0.25rem 0;
  font-size: 0.875rem;
}

/* Simulate Tab */
.simulate-tab {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.simulate-tab > .p-card {
  flex: 1;
  min-width: 300px;
}

.sim-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-row label {
  font-size: 0.875rem;
  color: #94a3b8;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

/* Evolution Tab */
.evolution-tab {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.evolution-controls {
  display: flex;
  gap: 1rem;
  align-items: center;
  padding: 0.5rem;
  background: var(--p-surface-ground);
  border-radius: 8px;
}

.species-select {
  width: 250px;
}

.evolution-charts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.evolution-charts .p-card {
  background: var(--p-surface-card);
}

.evolution-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: var(--p-text-color-secondary);
}

.evolution-placeholder p {
  margin-top: 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.stat-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  background: var(--p-surface-ground);
  border-radius: 8px;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--p-text-color-secondary);
  cursor: help;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  margin-top: 0.25rem;
}

.stat-value.positive {
  color: #22c55e;
}

.stat-value.negative {
  color: #ef4444;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: var(--p-text-color-secondary);
  font-style: italic;
}

/* Sandbox Tab */
.sandbox-tab {
  height: 100%;
}

.sandbox-map-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--p-surface-border);
  background: var(--p-surface-card);
}

.sandbox-toolbar {
  border: none;
  padding: 0.5rem;
}

.monster-select {
  width: 180px;
}

.map-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #000;
  cursor: crosshair;
  outline: none;
}

.map-wrapper:focus {
  outline: 2px solid #60a5fa;
}

.map-instructions {
  padding: 0.5rem;
  text-align: center;
  font-size: 0.8rem;
  opacity: 0.7;
}

.sandbox-panels {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  height: 100%;
  overflow-y: auto;
  padding: 0.5rem;
}

.sandbox-panels :deep(.p-panel-header) {
  padding: 0.5rem 1rem;
}

.sandbox-panels :deep(.p-panel-content) {
  padding: 0.75rem;
}

.sim-controls {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.speed-slider {
  flex: 1;
}

.tick-display {
  text-align: center;
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  flex-wrap: wrap;
}

.combat-toggle {
  background: var(--p-surface-ground);
  padding: 0.5rem;
  border-radius: 6px;
}

.combat-toggle label {
  cursor: pointer;
}

.monster-hp-edit {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.decision-log-panel :deep(.p-panel-content) {
  padding: 0;
}

.log-expansion {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  padding: 1rem;
}

.state-breakdown ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.state-breakdown li {
  font-size: 0.8rem;
  padding: 0.2rem 0;
}

.q-values-table h5,
.state-breakdown h5 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: var(--p-primary-color);
}

.q-highlight {
  color: #22c55e;
  font-weight: bold;
}

.refresh-button {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
}

.mt-2 {
  margin-top: 0.5rem;
}

.w-full {
  width: 100%;
}
</style>

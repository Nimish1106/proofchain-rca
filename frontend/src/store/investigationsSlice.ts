import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { apiClient } from '../api/client';
import type {
  Investigation,
  InvestigationCreatePayload,
  InvestigationUpdatePayload,
} from '../types/api';

interface InvestigationsState {
  items: Investigation[];
  total: number;
  selected: Investigation | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  apiHealthy: boolean | null;
}

const initialState: InvestigationsState = {
  items: [],
  total: 0,
  selected: null,
  loading: false,
  saving: false,
  error: null,
  apiHealthy: null,
};

export const checkApiHealth = createAsyncThunk('investigations/health', async () => {
  await apiClient.getHealth();
  return true;
});

export const fetchInvestigations = createAsyncThunk(
  'investigations/fetchAll',
  async () => apiClient.listInvestigations(100, 0),
);

export const fetchInvestigationById = createAsyncThunk(
  'investigations/fetchOne',
  async (id: string) => apiClient.getInvestigation(id),
);

export const createInvestigation = createAsyncThunk(
  'investigations/create',
  async (payload: InvestigationCreatePayload) => apiClient.createInvestigation(payload),
);

export const updateInvestigation = createAsyncThunk(
  'investigations/update',
  async ({ id, payload }: { id: string; payload: InvestigationUpdatePayload }) =>
    apiClient.updateInvestigation(id, payload),
);

const investigationsSlice = createSlice({
  name: 'investigations',
  initialState,
  reducers: {
    setSelectedInvestigation(state, action: { payload: Investigation | null }) {
      state.selected = action.payload;
    },
    clearInvestigationError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(checkApiHealth.fulfilled, (state) => {
        state.apiHealthy = true;
      })
      .addCase(checkApiHealth.rejected, (state) => {
        state.apiHealthy = false;
      })
      .addCase(fetchInvestigations.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchInvestigations.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
      })
      .addCase(fetchInvestigations.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? 'Failed to load investigations';
      })
      .addCase(fetchInvestigationById.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchInvestigationById.fulfilled, (state, action) => {
        state.loading = false;
        state.selected = action.payload;
      })
      .addCase(fetchInvestigationById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? 'Failed to load investigation';
      })
      .addCase(createInvestigation.pending, (state) => {
        state.saving = true;
        state.error = null;
      })
      .addCase(createInvestigation.fulfilled, (state, action) => {
        state.saving = false;
        state.items.unshift(action.payload);
        state.total += 1;
        state.selected = action.payload;
      })
      .addCase(createInvestigation.rejected, (state, action) => {
        state.saving = false;
        state.error = action.error.message ?? 'Failed to create investigation';
      })
      .addCase(updateInvestigation.pending, (state) => {
        state.saving = true;
        state.error = null;
      })
      .addCase(updateInvestigation.fulfilled, (state, action) => {
        state.saving = false;
        state.selected = action.payload;
        const idx = state.items.findIndex((i) => i.id === action.payload.id);
        if (idx >= 0) state.items[idx] = action.payload;
      })
      .addCase(updateInvestigation.rejected, (state, action) => {
        state.saving = false;
        state.error = action.error.message ?? 'Failed to update investigation';
      });
  },
});

export const { setSelectedInvestigation, clearInvestigationError } =
  investigationsSlice.actions;
export default investigationsSlice.reducer;

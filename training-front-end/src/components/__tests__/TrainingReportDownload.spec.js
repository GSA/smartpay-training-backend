import { describe, it, expect, beforeEach } from 'vitest';
import { mount, flushPromises  } from '@vue/test-utils'
import { vi } from 'vitest';
import TrainingReportDownload from '../TrainingReportDownload.vue';
import ReportRepository from '../ReportRepository.vue';
import { profile } from '../../stores/user';

// Mocking the ReportUtilities module
vi.mock('../ReportUtilities.vue', () => ({
    default: {
        downloadBlobAsFile: vi.fn(), // Mock this method to do nothing
    },
}));

const agency_api = [
    { 'id': 1, 'name': 'General Services Administration', 'bureaus': []},
    { 'id': 2,
        'name': 'Department of the Treasury',
        'bureaus': [
            {'id': 3, 'name': 'United States Mint'},
            {'id': 4, 'name': 'Financial Crimes Enforcement'}
        ]
    },
    { 'id': 5, 'name': 'Department of the Interior', 'bureaus': []}
]

describe('TrainingReportDownload.vue', () => {
    let wrapper;

    beforeEach(async () => {
        // Reset all mocks before each test
        vi.clearAllMocks();

        vi.spyOn(global, 'fetch').mockImplementation(() => {
            return Promise.resolve({ok: true, status:200, json: () => Promise.resolve(agency_api) })
        })

        // Set the profile mock with Report role
        profile.set({ name: 'Amelia Sedley', jwt: 'some-token-value', roles: ['Report'], 
            report_agencies: [
                {name: 'General Services Administration', bureau: null, id: 1},
                {name: 'Department of the Treasury', bureau: 'Financial Crimes Enforcement', id: 4},
                {name: 'Department of the Interior', bureau: null, id: 5}
            ] });

        wrapper = await mount(TrainingReportDownload, {
            global: {
                stubs: {
                    // Stub child components that are not essential for the test
                    USWDSAlert: true,
                    ValidatedSelect: true,
                    ValidatedDateRangePicker: true,
                    ValidatedCheckboxGroup: true,
                    SpinnerGraphic: true,
                },
            },
        });
    });

    it('renders the form when the user is an Report', () => {
        expect(wrapper.html()).toContain('Enter Report Parameters');
        expect(wrapper.find('form').exists()).toBe(true);
    });

    it('displays an error message when the user is not authorized', async () => {
        // Change the profile to non report user
        profile.set({ name: 'Amelia Sedley', jwt: 'some-token-value', roles: [] });

        await wrapper.vm.$nextTick();

        expect(wrapper.html()).toContain('You are not authorized to receive reports.');
        expect(wrapper.find('form').exists()).toBe(false);
    });

    it('handles errors during report download', async () => {
        ReportRepository.downloadTrainingCompletionReport = vi.fn(() => Promise.reject(new Error('Failed to download')));

        await wrapper.find('form').trigger('submit.prevent');

        expect(wrapper.vm.error.message).toBe('Failed to download');
    });

    it('shows a success message after a successful report download', async () => {
        ReportRepository.downloadTrainingCompletionReport = vi.fn(() =>
            Promise.resolve({
                blob: () => new Blob(['mock-csv-content'], { type: 'text/csv' }),
            })
        );

        // Trigger the form submission
        await wrapper.find('form').trigger('submit.prevent');

        // Wait for all pending promises and Vue updates to complete
        await flushPromises();

        // Assert that the success message is shown
        expect(wrapper.vm.showSuccessMessage).toBe(true);
    });

    it('displays a spinner while the report is loading', async () => {
        const downloadPromise = new Promise(() => {}); // Mock a pending download
        ReportRepository.downloadTrainingCompletionReport = vi.fn(() => downloadPromise);

        await wrapper.find('form').trigger('submit.prevent');

        expect(wrapper.vm.showSpinner).toBe(true);
    });
});
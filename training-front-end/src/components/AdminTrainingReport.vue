<script setup>
  import { ref, onErrorCaptured, reactive, watch } from "vue"
  import { useStore } from '@nanostores/vue'
  import { profile} from '../stores/user'
  import { computed } from "vue"
  import { bureauList, agencyList, setSelectedAgencyId} from '../stores/agencies'
  import USWDSAlert from './USWDSAlert.vue'
  import ValidatedDateRangePicker from "./form-components/ValidatedDateRangePicker.vue"
  import { useVuelidate } from '@vuelidate/core';
  import SpinnerGraphic from './SpinnerGraphic.vue'
  import ValidatedCheckboxGroup from "./form-components/ValidatedCheckboxGroup.vue"
  import ReportUtilities from './ReportUtilities.vue';
  import AdminRepository from './AdminRepository.vue';
  import USWDSComboBox from "./form-components/USWDSComboBox.vue";

  const error = ref()
  const user = useStore(profile)
  const isAdminUser = computed(() => user.value.roles.includes('Admin'))
  const agency_options = useStore(agencyList)
  const bureaus = useStore(bureauList)
  const showSuccessMessage = ref(false)
  const isLoading = ref(false)
  const showSpinner = ref(false)

  //Properties 
  const user_input = reactive({
    agency_id: undefined,
    bureau_id: undefined,
    quiz_names: undefined,
    completion_date_range: undefined,
  })

  const quiz_names_options = [
    { value: 'Fleet Training For Program Coordinators', label: 'Fleet Training For Program Coordinators' },
    { value: 'Purchase Training for Card/Account Holders and Approving Officials', label: 'Purchase Training for Card/Account Holders and Approving Officials' },
    { value: 'Purchase Training For Program Coordinators', label: 'Purchase Training For Program Coordinators' },
    { value: 'Travel Training for Agency/Organization Program Coordinators', label: 'Travel Training for Agency/Organization Program Coordinators' },
    { value: 'Travel Training for Card/Account Holders and Approving Officials', label: 'Travel Training for Card/Account Holders and Approving Officials' },
  ];

  const validation_info = {
    agency_id: {},
    bureau_id: {},
    completion_date_range: {},
    quiz_names: {}
  }

  const v_all_info$ = useVuelidate(validation_info, user_input)

  watch(() => user_input.agency_id, async() => {
    setSelectedAgencyId(user_input.agency_id)
    user_input.bureau_id = undefined
  })

	function setError(event){
    error.value = event
	}

  //format dates from uswds standard to the format needed for backend 
  const formatDateToYYYYMMDD = (dates) => {
    return dates ? dates.map(date => (date ? new Date(date).toISOString() : null)) : [];
  };

  async function downloadReport() {
    isLoading.value = true
    showSpinner.value = true
    error.value = undefined
    showSuccessMessage.value = false

    try {
      const dates = formatDateToYYYYMMDD(user_input.completion_date_range)
      const model = {
        'agency_id': user_input.agency_id || null,
        'bureau_id': user_input.bureau_id || null,
        'completion_date_start': dates[0] || null,
        'completion_date_end': dates[1] || null,
        'quiz_names': user_input.quiz_names || null
      }
      let response = await AdminRepository.downloadTrainingReport(model)
      const blob = await response.blob();
      ReportUtilities.downloadBlobAsFile(blob, 'SmartPayTrainingReport.csv')
      showSuccessMessage.value = true

    } catch (error) {
      setError(error)
    }

    isLoading.value = false
    showSpinner.value = false
  }

  onErrorCaptured((err) => {
    if (err.message == 'Unauthorized'){
      err = {
        name: 'You are not authorized to receive admin reports.',
        message: 'Your email account is not authorized to access admin reports. If you should be authorized, you can <a class="usa-link" href="mailto:gsa_smartpay@gsa.gov">contact the GSA SmartPay® team</a> to gain access.'
      }
      setError(err)
    }
    return false
  })
</script>

<template>
  <section 
    v-if="isAdminUser"  
    class="usa-prose"
  >
    <div class="padding-top-4 padding-bottom-4 grid-container">
      <h2>Enter Report Parameters</h2>
      <p>
        The GSA SmartPay Training Report has no required parameters. 
      </p>
      <p>
        <b>Note:</b> If a report is generated with an individual completing multiple trainings, each training will be listed separately on the report.
      </p>
      <form
        ref="form"
        class="usa-form usa-form--large margin-bottom-3"
        data-test="gspc-form"
        @submit.prevent="downloadReport"
      >
        <ValidatedDateRangePicker
          v-model="user_input.completion_date_range"
          client:load
          :validator="v_all_info$.completion_date_range"
          label="Completion date range"
          name="Completion date range"
        />
        <ValidatedCheckboxGroup
          v-model="user_input.quiz_names"
          :options="quiz_names_options"
          :validator="v_all_info$.quiz_names"
          name="Quiz type(s)"
          legend="Quiz type(s)"
          class="margin-top-4"
        />
        <USWDSComboBox
          v-model="user_input.agency_id"
          client:load
          :validator="v_all_info$.agency_id"
          :items="agency_options"
          label="Agency / organization"
          name="Agency"
        />
        <USWDSComboBox
          v-if="bureaus.length"
          v-model="user_input.bureau_id"
          client:load
          :validator="v_all_info$.bureau_id"
          :items="bureaus"
          label="Sub-agency, organization, or bureau"
          name="Bureau"
        />
        <input
          class="usa-button"
          type="submit"
          value="Submit"
          :disabled="isLoading"
          data-test="submit"
        >
        <div>
          <USWDSAlert
            v-if="error"
            status="error"
            class="usa-alert--slim"
            :has-heading="false"
          >
            {{ error }}
          </USWDSAlert>
          <USWDSAlert
            v-if="showSuccessMessage"
            status="success"
            class="usa-alert--slim"
            :has-heading="false"
          >
            Report has been generated.
          </USWDSAlert>
        </div>
        <div class="grid-row grid-gap margin-top-3">
          <!--display spinner along with submit button in one row for desktop-->
          <div
            v-if="showSpinner"
            class="display-none tablet:display-block tablet:grid-col-1 tablet:padding-top-3 tablet:margin-left-neg-1"
          >
            <SpinnerGraphic />
          </div>
        </div>
        <!--display spinner under submit button for mobile view-->
        <div
          v-if="showSpinner"
          class="tablet:display-none margin-top-1 text-center"
        >
          <SpinnerGraphic />
        </div>
      </form>
    </div>
  </section>

  <section v-else>
    <USWDSAlert      
      status="error"
      class="usa-alert"
      heading="You are not authorized to receive reports."
    >
      Your email account is not authorized to access admin reports. If you should be authorized, you can 
      <a
        class="usa-link"
        href="mailto:gsa_smartpay@gsa.gov"
      >
        contact the GSA SmartPay team
      </a> to gain access.
    </USWDSAlert>
  </section>
</template>
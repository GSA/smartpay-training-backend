<script setup>
  import { ref, onErrorCaptured, onBeforeMount } from 'vue';
  import { useStore } from '@nanostores/vue'
  import { profile} from '../stores/user'
  import USWDSAlert from './USWDSAlert.vue'
  import Loginless from './LoginlessFlow.vue';
  import GspcQuestions from './GspcQuestions.vue';
  import FileDownLoad from "./icons/FileDownload.vue"


  onErrorCaptured((err) => {
    setError(err)
    return false
  })

  const props = defineProps({
    'certPassed': {
      type: Boolean,
      required: false,
      default: false
    },
    'certId': {
      type: Number,
      required: false,
      default: null
    },
    'certFailed': {
      type: Boolean,
      required: false,
      default: false
    },
    'error': {
      type: Object,
      required: false,
      default: null
    },
  })

  const user = useStore(profile)
  const base_api_url = import.meta.env.PUBLIC_API_BASE_URL
  const base_url = import.meta.env.BASE_URL
  const certPassed = ref(props.certPassed)
  const certId = ref(props.certId)
  const certFailed = ref(props.certFailed)
  const quizStarted = ref(false)
  const quizSubmitted = ref(false)
  const error = ref(props.error)
  let gspcInviteId = ""
  let redirectGspcInviteIdString = ""
  const certTypeGspc = 2

  const questions = 
    [{"id": 0, 
        "text": "I have met the coursework requirement during the GSA SmartPay Training Forum by attending at least two GSA Qualifying classes and at least five Bank/Brand Qualifying classes, as outlined in Smart Bulletin No. 022.", 
        "type": "MultipleChoiceSingleSelect",  
        "choices": [{"id": 0, "text": "Yes", "correct": true}, {"id": 1, "text": "No", "correct": false}]}, 
      {"id": 1, 
        "text": "I have met the experience requirement by having a minimum of six months of continuous, hands-on experience working in an agency/organization's GSA SmartPay Program prior to receiving the GSPC.", 
        "type": "MultipleChoiceSingleSelect", 
        "choices": [{"id": 0, "text": "Yes", "correct": true}, {"id": 1, "text": "No", "correct": false}]},
      ]


  onBeforeMount(async () => {
    const urlParams = new URLSearchParams(window.location.search);
    gspcInviteId = urlParams.get('gspcInviteId')
    redirectGspcInviteIdString = 'gspcInviteId=' + gspcInviteId
  })

  function startLoading() {
    error.value = undefined
  }

	function setError(event){
    error.value = event
	}

  function startQuiz() {
    quizStarted.value = true
  }

  async function submitGspcRegistration(user_answers) {
    const url = `${base_api_url}/api/v1/gspc/submission`
    quizSubmitted.value = true
    let res
    
    try {
      res = await fetch(url, { 
        method: "POST", 
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.value.jwt}`
        },
        body: JSON.stringify({'responses':{'responses': user_answers}, 'gspc_invite_id': gspcInviteId}) 
      })
    } catch {
      const err = new Error("There was a problem connecting with the server")
      err.name = "Server Error"
      setError(err)
      return 
    }
    if (!res.ok){
      // non 2xx response from server
      // TODO: this could happen with an expired jwt
      // should offer solution for user in that case.
      const e = new Error("There was a problem connecting with the server")
      e.name = "Server Error"
      setError(e)
    }
    var result = await res.json()
    if(result.passed){
      certPassed.value = true
      certId.value = result.cert_id
    } else{
      certFailed.value = true
    }
  }
</script>

<template>
  <div
    class="padding-top-4 padding-bottom-4"
    :class="{'bg-base-lightest': quizStarted && !quizSubmitted}"
  >
    <div
      class="grid-container"
      data-test="post-submit"
    >
      <div class="grid-row">
        <div class="tablet:grid-col-12">
          <USWDSAlert
            v-if="error"
            class="tablet:grid-col-12"
            status="error"
            :heading="error.name"
          >
            {{ error.message }}
          </USWDSAlert>
          <Suspense>
            <template #fallback>
              …Loading
            </template>
            <Loginless
              page-id="gspc_registration"
              title="gspc_registration"
              :header="header"
              link-destination-text="the GSA SmartPay Program Certification (GSPC)"
              :parameters="redirectGspcInviteIdString"
              @start-loading="startLoading"
              @error="setError"
            >
              <template #initial-greeting>
                <h2>Verify GSPC coursework and experience</h2>
                <p>Enter your email address to get access to verify your coursework and experience to receive your GSA SmartPay Program Certification (GSPC). You'll receive an email with an access link.</p>
              </template>
              
              <template #more-info>
                <h2>Welcome!</h2>
                <p>Before verifying your GSPC coursework and experience, you'll need to create and complete your profile.</p>
              </template>
              <div v-if="certPassed">
                <h2>Congratulations You Earned Your GSA SmartPay Program Certificate (GSPC)</h2>
                <p>You have met the requirements to earn a GSA SmartPay Program Certificate (GSPC). Your certificate has been emailed to you. Or, you may download your certificate below.</p>
                <form
                  :action="`${base_api_url}/api/v1/certificate/${certTypeGspc}/${certId}`" 
                  method="post"
                >
                  <input 
                    type="hidden"
                    name="jwtToken"
                    :value="user.jwt"
                  >
                  <button
                    class="usa-button"
                    type="submit"
                  >
                    <FileDownLoad /> Download your certificate
                  </button>
                  <br><br>
                  <a :href="base_url">Return to the GSA SmartPay Training Home Page</a>
                </form>
              </div>
              <div v-else-if="certFailed">
                <h2>You Don't Meet the Requirements for GSA SmartPay Program Certification (GSPC)</h2>
                <p>Once you have met the coursework and experience requirement of six months of continuous, hands-on experience working with the GSA SmartPay program please return to the link  in your email to reapply.</p>
                <p>If you have any questions, please reference <a href="https://smartpay.gsa.gov/policies-and-audits/smart-bulletins/022/">Smart Bulletin No. 022</a> or contact the GSPC Program Manager at <a href="mailto:smartpaygspc@gsa.gov">smartpaygspc@gsa.com</a>.</p>
                <a :href="base_url">Return to the GSA SmartPay Training Home Page</a>
              </div>
              <div v-else>
                <GspcQuestions
                  :questions="questions"
                  class="desktop:grid-col-8"
                  @submit-gspc-registration="submitGspcRegistration"
                  @start-quiz="startQuiz"
                />
              </div>
            </Loginless>
          </Suspense>
        </div>
      </div>
    </div>
  </div>
</template>
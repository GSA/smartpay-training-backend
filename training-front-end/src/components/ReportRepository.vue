<script>

import {useStore} from "@nanostores/vue";
import {profile} from "../stores/user.js";

const user = useStore(profile)
const base_url = import.meta.env.PUBLIC_API_BASE_URL
const downloadTrainingCompletionReport = async function(filterData){
  const response = await fetch(`${base_url}/api/v1/users/download-smartpay-training-report`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${user.value.jwt}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(filterData)
  });
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message)
  }

  return await response //needs to be returned as raw not json
}

export default {
  downloadTrainingCompletionReport
}

</script>

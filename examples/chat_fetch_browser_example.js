/**
 * Browser example: POST /chat with FormData (legacy catalog flow).
 * Not run by pytest — kept for manual API debugging.
 */
const data = {
  params: {
    promptList: [],
    input: "…",
    conversationTitle: "…",
    channelName: "…",
    extraInfo: [],
  },
};

const formData = new FormData();
formData.append("params", JSON.stringify(data.params));

fetch("/chat", { body: formData, method: "POST" })
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.json();
  })
  .then((json) => console.log("Received JSON response:", json))
  .catch((error) => console.error("Error:", error));

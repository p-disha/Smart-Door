
// WP-1
function submitToVisitorForm(e) {
	console.log(document.getElementById("name-input").value);
	console.log(document.getElementById("phone-input").value);
	var apigClient = apigClientFactory.newClient();
	var params = {};

	var body = {
        'message': {
			'name-input':document.getElementById("name-input").value,
			'phone-input':document.getElementById("phone-input").value
		}
    }
	var additionalParams = {};
    apigClient.visitorInfoPost(params, body, additionalParams)
    .then(function(result){
        console.log(result);
	alert(result["data"]["body"]);
    }).catch( function(result){
        //This is where you would put an error callback
        console.log(result)
		
    });
}


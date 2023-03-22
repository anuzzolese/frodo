
$(document).ready(function(){
	$("#btn-opts").click(showOpts);
	$("#btn-examples").click(showExamples);
	$(".btn-use").click(useExample);
	$(".btn-read").click(submit);
	$("#result").hide();
});

function showOpts(){
    hideExamples();
	$("#options").show();
	$("#btn-opts").html("Hide options");
	$("#btn-opts").unbind("click");
	$("#btn-opts").click(hideOpts);
}

function hideOpts(){
	$("#options").hide();
	$("#btn-opts").html("Show options");
	$("#btn-opts").unbind("click");
	$("#btn-opts").click(showOpts);
}

function showExamples(){
	hideOpts();
	$("#examples").show();
	$("#btn-examples").html("Hide examples");
	$("#btn-examples").unbind("click");
	$("#btn-examples").click(hideExamples);
}

function hideExamples(){
	$("#examples").hide();
	$("#btn-examples").html("Show examples");
	$("#btn-examples").unbind("click");
	$("#btn-examples").click(showExamples);
}

function useExample(){
	var example = $(".example", $(this).parent()).html();
	$("#text").html(example);
}

function submit(event){
	
	event.preventDefault();
	var endpoint = jQuery(".btn-read").attr("endpoint");
	jQuery("#result").hide();
	jQuery(this).parent().append('<div class="loading"><img style="width: 150px" src="' + jQuery('base').attr('href') + '/static/img/giphy.gif"/></div>');
    
    data = {
	    text: jQuery("#text").val()
    }
    
    jQuery.get(endpoint, data).done(function(data){
		jQuery(".loading").remove();
		
		jQuery("#result").html("<h3>Result</h3><pre>" + data + "</pre>");
		jQuery("#result").show();

	});
}
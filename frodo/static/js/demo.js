
$(document).ready(function(){
	$("#btn-opts").click(showOpts);
	$("#btn-examples").click(showExamples);
	$(".btn-use").click(useExample);
	$(".btn-read").click(submit)
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
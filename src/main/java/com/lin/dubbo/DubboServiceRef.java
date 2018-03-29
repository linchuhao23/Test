package com.lin.dubbo;

import org.springframework.stereotype.Component;

import com.alibaba.dubbo.config.annotation.Reference;
import com.lin.dubbo.api.DubboService;

@Component("DubboServiceRef")
public class DubboServiceRef /*implements DubboService*/ {
	
	//@Reference(group="DubboService", version="1.0")
	//private DubboService dubboService;

	//@Override
	public String getDubboServiceName() {
		//return dubboService.getDubboServiceName();
		return null;
	}

}

let s:script_dir_path=expand('<sfile>:p:h')

function! vebugger#xdebug#start()
	let l:debuggerExe=vebugger#util#getToolFullPath('python', 'xcode', 'python3')
	let l:debugger=vebugger#std#startDebugger(shellescape(l:debuggerExe)
				\.' '.s:script_dir_path.'/xdebug_wrapper.py ')

	let l:debugger.state.xdebug={'shellBuffer':0}

	if !has('win32')
		call vebugger#std#openShellBuffer(l:debugger)
		let l:debugger.state.xdebug.shellBuffer=1
	endif

	call l:debugger.addReadHandler(function('vebugger#xdebug#_readProgramOutput'))
	call l:debugger.addReadHandler(function('vebugger#xdebug#_readLocation'))
	call l:debugger.addReadHandler(function('vebugger#xdebug#_readLog'))
	call l:debugger.addReadHandler(function('vebugger#xdebug#_readFinish'))
	call l:debugger.addReadHandler(function('vebugger#xdebug#_readEvaluatedExpressions'))

	call l:debugger.setWriteHandler('std','flow',function('vebugger#xdebug#_writeFlow'))
	call l:debugger.setWriteHandler('std','breakpoints',function('vebugger#xdebug#_writeBreakpoints'))
	call l:debugger.setWriteHandler('std','closeDebugger',function('vebugger#xdebug#_closeDebugger'))
	call l:debugger.setWriteHandler('std','evaluateExpressions',function('vebugger#xdebug#_requestEvaluateExpression'))
	call l:debugger.setWriteHandler('std','executeStatements',function('vebugger#xdebug#_executeStatements'))

	call l:debugger.generateWriteActionsFromTemplate()

	call l:debugger.std_addAllBreakpointActions(g:vebugger_breakpoints)

	return l:debugger
endfunction

function! vebugger#xdebug#_readProgramOutput(pipeName,line,readResult,debugger)
	if 'out'==a:pipeName && (a:line=~'\v^dbgp_out:' || a:line=~'\v^dbgp_err:')
		let a:readResult.std.programOutput={'line':strpart(a:line, 9)}
	endif
endfunction

function! vebugger#xdebug#_readLocation(pipeName,line,readResult,debugger)
	if 'out'==a:pipeName && a:line=~'\v^dbgp_loc:'
		let l:matches=matchlist(a:line,'\v^dbgp_loc:\s([^:]+):(\d+)')
		if 2<len(l:matches)
			let l:file=l:matches[1]
			let l:file=fnamemodify(l:file,':p')
			let a:readResult.std.location={
						\'file':(l:file),
						\'line':str2nr(l:matches[2])}
		endif
	endif
endfunction

function! vebugger#xdebug#_readLog(pipeName,line,readResult,debugger)
	if 'out'==a:pipeName && a:line=~'\v^dbgp_log:'
		let a:readResult.std.programOutput={'line':'xdebug: '.strpart(a:line, 9)}
	endif
endfunction

function! vebugger#xdebug#_readFinish(pipeName,line,readResult,debugger)
	if 'out'==a:pipeName && a:line=~'\v^dbgp_end:'
		let a:readResult.std.programOutput={'line':'xdebug: Finished. '.strpart(a:line, 9)}
		let a:readResult.std.programFinish={'finish':1}
	endif
endfunction

function! vebugger#xdebug#_writeFlow(writeAction,debugger)
	if 'stepin'==a:writeAction
		call a:debugger.writeLine('step_into')
	elseif 'stepover'==a:writeAction
		call a:debugger.writeLine('step_over')
	elseif 'stepout'==a:writeAction
		call a:debugger.writeLine('step_out')
	elseif 'continue'==a:writeAction
		call a:debugger.writeLine('run')
	endif
endfunction

function! vebugger#xdebug#_closeDebugger(writeAction,debugger)
	call a:debugger.writeLine('stop')
endfunction

function! vebugger#xdebug#_writeBreakpoints(writeAction,debugger)
	for l:breakpoint in a:writeAction
		if 'add'==(l:breakpoint.action)
			call a:debugger.writeLine('breakpoint_set -t line -f '.fnameescape(l:breakpoint.file).' -n '.l:breakpoint.line)
		elseif 'remove'==l:breakpoint.action
			call a:debugger.writeLine('breakpoint_remove -t line -f '.fnameescape(l:breakpoint.file).' -n '.l:breakpoint.line)
		endif
	endfor
endfunction

function! vebugger#xdebug#_requestEvaluateExpression(writeAction,debugger)
	for l:evalAction in a:writeAction
		call a:debugger.writeLine('eval -- '.l:evalAction.expression)
	endfor
endfunction

function! vebugger#xdebug#_executeStatements(writeAction,debugger)
	for l:evalAction in a:writeAction
		if has_key(l:evalAction,'statement')
			"Use eval to run the statement - but first we need to remove the ;
			call a:debugger.writeLine('eval -- '.substitute(l:evalAction.statement,'\v;\s*$','',''))
		endif
	endfor
endfunction

function! vebugger#xdebug#_readEvaluatedExpressions(pipeName,line,readResult,debugger) dict
	if 'out' == a:pipeName
		if has_key(self, 'nextExpressionToBePrinted') && a:line=~'\v^debugger_output:'
			let l:matches=matchlist(a:line,'\v^[^\$]*\$(\d+) \= (.*)$')
			if 2<len(l:matches)
				let l:expression=l:matches[1]
				let l:value=l:matches[2]
				let a:readResult.std.evaluatedExpression={
							\'expression':self.nextExpressionToBePrinted,
							\'value':(l:value)}
			endif
			call remove(self,'nextExpressionToBePrinted')
		else
			let l:matches=matchlist(a:line,'\v^print (.+)$')
			if 1<len(l:matches)
				let self.nextExpressionToBePrinted=l:matches[1]
			endif
		endif
	endif
endfunction


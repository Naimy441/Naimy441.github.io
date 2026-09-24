on run
    tell application "System Events"
        set targetProcess to missing value
        repeat 120 times
            try
                set targetProcess to first application process whose bundle identifier is "com.transact.mobileorder"
                exit repeat
            end try
            delay 0.25
        end repeat

        if targetProcess is missing value then
            error "Could not find the running Mobile Order accessibility process."
        end if

        tell targetProcess
            set frontmost to true
            repeat 120 times
                try
                    if (exists window 1) then
                        set candidateElements to entire contents of window 1
                        set backButton to missing value
                        repeat with candidateElement in candidateElements
                            try
                                if (role of candidateElement as text) is "AXButton" and (description of candidateElement as text) is "Back" then
                                    set backButton to candidateElement
                                else if (role of candidateElement as text) is "AXGroup" and (help of candidateElement as text) is "Double tap to select" then
                                    set childElements to entire contents of candidateElement
                                    set isRestaurantRow to false
                                    repeat with childElement in childElements
                                        try
                                            if (description of childElement as text) contains "Open." then
                                                set isRestaurantRow to true
                                            end if
                                        end try
                                    end repeat
                                    if isRestaurantRow then
                                        repeat with childElement in childElements
                                            try
                                                if (role of childElement as text) is "AXButton" and (description of childElement as text) is "chevron" then
                                                    click childElement
                                                    return "Clicked the first open restaurant."
                                                end if
                                            end try
                                        end repeat
                                    end if
                                end if
                            end try
                        end repeat
                        if backButton is not missing value then
                            click backButton
                            delay 0.25
                        end if
                    end if
                end try
                delay 0.25
            end repeat
        end tell
    end tell

    error "No open restaurant button appeared in Mobile Order."
end run

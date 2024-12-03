(
    doHighlightElements = true
) => {
    let highlightIndex = 0; // Reset highlight index

    function highlightElement(element, index, parentIframe = null) {
        // Create or get highlight container
        let container = document.getElementById('playwright-highlight-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'playwright-highlight-container';
            container.style.position = 'fixed';
            container.style.pointerEvents = 'none';
            container.style.top = '0';
            container.style.left = '0';
            container.style.width = '100%';
            container.style.height = '100%';
            container.style.zIndex = '2147483647'; // Maximum z-index value
            document.documentElement.appendChild(container);
        }

        // Create highlight overlay
        const overlay = document.createElement('div');
        overlay.style.position = 'absolute';
        overlay.style.border = '2px solid red';
        overlay.style.pointerEvents = 'none';
        overlay.style.boxSizing = 'border-box';

        // Position overlay based on element
        const rect = element.getBoundingClientRect();
        let top = rect.top;
        let left = rect.left;

        // Adjust position if element is inside an iframe
        if (parentIframe) {
            const iframeRect = parentIframe.getBoundingClientRect();
            top += iframeRect.top;
            left += iframeRect.left;
        }

        overlay.style.top = `${top}px`;
        overlay.style.left = `${left}px`;
        overlay.style.width = `${rect.width}px`;
        overlay.style.height = `${rect.height}px`;

        // Create label
        const label = document.createElement('div');
        label.className = 'playwright-highlight-label';
        label.style.position = 'absolute';
        label.style.background = 'red';
        label.style.color = 'white';
        label.style.padding = '2px 6px';
        label.style.borderRadius = '10px';
        label.style.fontSize = '12px';
        label.textContent = index;
        label.style.top = `${top - 20}px`;
        label.style.left = `${left}px`;


        // Add to container
        container.appendChild(overlay);
        container.appendChild(label);


        // Store reference for cleanup
        element.setAttribute('browser-user-highlight-id', `playwright-highlight-${index}`);

        return index + 1;
    }


    // Helper function to generate XPath as a tree
    function getXPathTree(element, stopAtBoundary = true) {
        const segments = [];
        let currentElement = element;

        while (currentElement && currentElement.nodeType === Node.ELEMENT_NODE) {
            // Stop if we hit a shadow root or iframe
            if (stopAtBoundary && (currentElement.parentNode instanceof ShadowRoot || currentElement.parentNode instanceof HTMLIFrameElement)) {
                break;
            }

            let index = 0;
            let sibling = currentElement.previousSibling;
            while (sibling) {
                if (sibling.nodeType === Node.ELEMENT_NODE &&
                    sibling.nodeName === currentElement.nodeName) {
                    index++;
                }
                sibling = sibling.previousSibling;
            }

            const tagName = currentElement.nodeName.toLowerCase();
            const xpathIndex = index > 0 ? `[${index + 1}]` : '';
            segments.unshift(`${tagName}${xpathIndex}`);

            currentElement = currentElement.parentNode;
        }

        return segments.join('/');
    }

    // Helper function to check if element is accepted
    function isElementAccepted(element) {
        const leafElementDenyList = new Set(['svg', 'script', 'style', 'link', 'meta']);
        return !leafElementDenyList.has(element.tagName.toLowerCase());
    }

    // Helper function to check if element is interactive
    function isInteractiveElement(element) {
        // Base interactive elements and roles
        const interactiveElements = new Set([
            'a', 'button', 'details', 'embed', 'input', 'label',
            'menu', 'menuitem', 'object', 'select', 'textarea', 'summary'
        ]);

        const interactiveRoles = new Set([
            'button', 'menu', 'menuitem', 'link', 'checkbox', 'radio',
            'slider', 'tab', 'tabpanel', 'textbox', 'combobox', 'grid',
            'listbox', 'option', 'progressbar', 'scrollbar', 'searchbox',
            'switch', 'tree', 'treeitem', 'spinbutton', 'tooltip',
            'menuitemcheckbox', 'menuitemradio'
        ]);

        const tagName = element.tagName.toLowerCase();
        const role = element.getAttribute('role');
        const ariaRole = element.getAttribute('aria-role');
        const tabIndex = element.getAttribute('tabindex');

        // Basic role/attribute checks
        const hasInteractiveRole = interactiveElements.has(tagName) ||
            interactiveRoles.has(role) ||
            interactiveRoles.has(ariaRole) ||
            tabIndex === '0';

        if (hasInteractiveRole) return true;

        // Get computed style
        const style = window.getComputedStyle(element);

        // Check if element has click-like styling
        // const hasClickStyling = style.cursor === 'pointer' ||
        //     element.style.cursor === 'pointer' ||
        //     style.pointerEvents !== 'none';

        // Check for event listeners
        const hasClickHandler = element.onclick !== null ||
            element.getAttribute('onclick') !== null ||
            element.hasAttribute('ng-click') ||
            element.hasAttribute('@click') ||
            element.hasAttribute('v-on:click');

        // Helper function to safely get event listeners
        function getEventListeners(el) {
            try {
                // Try to get listeners using Chrome DevTools API
                return window.getEventListeners?.(el) || {};
            } catch (e) {
                // Fallback: check for common event properties
                const listeners = {};

                // List of common event types to check
                const eventTypes = [
                    'click', 'mousedown', 'mouseup',
                    'touchstart', 'touchend',
                    'keydown', 'keyup', 'focus', 'blur'
                ];

                for (const type of eventTypes) {
                    const handler = el[`on${type}`];
                    if (handler) {
                        listeners[type] = [{
                            listener: handler,
                            useCapture: false
                        }];
                    }
                }

                return listeners;
            }
        }

        // Check for click-related events on the element itself
        const listeners = getEventListeners(element);
        const hasClickListeners = listeners && (
            listeners.click?.length > 0 ||
            listeners.mousedown?.length > 0 ||
            listeners.mouseup?.length > 0 ||
            listeners.touchstart?.length > 0 ||
            listeners.touchend?.length > 0
        );

        // Check for ARIA properties that suggest interactivity
        const hasAriaProps = element.hasAttribute('aria-expanded') ||
            element.hasAttribute('aria-pressed') ||
            element.hasAttribute('aria-selected') ||
            element.hasAttribute('aria-checked');

        // Check for form-related functionality
        const isFormRelated = element.form !== undefined ||
            element.hasAttribute('contenteditable') ||
            style.userSelect !== 'none';

        // Check if element is draggable
        const isDraggable = element.draggable ||
            element.getAttribute('draggable') === 'true';

        return hasAriaProps ||
            // hasClickStyling ||
            hasClickHandler ||
            hasClickListeners ||
            // isFormRelated ||
            isDraggable;

    }

    // Helper function to check if element is visible
    function isElementVisible(element) {
        const style = window.getComputedStyle(element);
        return element.offsetWidth > 0 &&
            element.offsetHeight > 0 &&
            style.visibility !== 'hidden' &&
            style.display !== 'none';
    }

    // Helper function to check if element is the top element at its position
    function isTopElement(element) {
        // Find the correct document context and root element
        let doc = element.ownerDocument;

        // If we're in an iframe, elements are considered top by default
        if (doc !== window.document) {
            return true;
        }

        // For shadow DOM, we need to check within its own root context
        const shadowRoot = element.getRootNode();
        if (shadowRoot instanceof ShadowRoot) {
            const rect = element.getBoundingClientRect();
            const point = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };

            try {
                // Use shadow root's elementFromPoint to check within shadow DOM context
                const topEl = shadowRoot.elementFromPoint(point.x, point.y);
                if (!topEl) return false;

                // Check if the element or any of its parents match our target element
                let current = topEl;
                while (current && current !== shadowRoot) {
                    if (current === element) return true;
                    current = current.parentElement;
                }
                return false;
            } catch (e) {
                return true; // If we can't determine, consider it visible
            }
        }

        // Regular DOM elements
        const rect = element.getBoundingClientRect();
        const point = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };

        try {
            const topEl = document.elementFromPoint(point.x, point.y);
            if (!topEl) return false;

            let current = topEl;
            while (current && current !== document.documentElement) {
                if (current === element) return true;
                current = current.parentElement;
            }
            return false;
        } catch (e) {
            return true;
        }
    }

    // Helper function to check if text node is visible
    function isTextNodeVisible(textNode) {
        const range = document.createRange();
        range.selectNodeContents(textNode);
        const rect = range.getBoundingClientRect();

        return rect.width !== 0 &&
            rect.height !== 0 &&
            rect.top >= 0 &&
            rect.top <= window.innerHeight &&
            textNode.parentElement?.checkVisibility({
                checkOpacity: true,
                checkVisibilityCSS: true
            });
    }


    // Function to traverse the DOM and create nested JSON
    function buildDomTree(node, parentIframe = null) {
        if (!node) return null;

        // Special case for text nodes
        if (node.nodeType === Node.TEXT_NODE) {
            const textContent = node.textContent.trim();
            if (textContent && isTextNodeVisible(node)) {
                return {
                    type: "TEXT_NODE",
                    text: textContent,
                    isVisible: true,
                };
            }
            return null;
        }

        // Check if element is accepted
        if (node.nodeType === Node.ELEMENT_NODE && !isElementAccepted(node)) {
            return null;
        }

        const nodeData = {
            tagName: node.tagName ? node.tagName.toLowerCase() : null,
            attributes: {},
            xpath: node.nodeType === Node.ELEMENT_NODE ? getXPathTree(node, true) : null,
            children: [],
        };

        // Copy all attributes if the node is an element
        if (node.nodeType === Node.ELEMENT_NODE && node.attributes) {
            // Use getAttributeNames() instead of directly iterating attributes
            const attributeNames = node.getAttributeNames?.() || [];
            for (const name of attributeNames) {
                nodeData.attributes[name] = node.getAttribute(name);
            }
        }

        if (node.nodeType === Node.ELEMENT_NODE) {
            const isInteractive = isInteractiveElement(node);
            const isVisible = isElementVisible(node);
            const isTop = isTopElement(node);

            nodeData.isInteractive = isInteractive;
            nodeData.isVisible = isVisible;
            nodeData.isTopElement = isTop;

            // Highlight if element meets all criteria and highlighting is enabled
            if (isInteractive && isVisible && isTop) {
                nodeData.highlightIndex = highlightIndex++;
                if (doHighlightElements) {
                    highlightElement(node, nodeData.highlightIndex, parentIframe);
                }
            }
        }

        // Only add iframeContext if we're inside an iframe
        // if (parentIframe) {
        //     nodeData.iframeContext = `iframe[src="${parentIframe.src || ''}"]`;
        // }

        // Only add shadowRoot field if it exists
        if (node.shadowRoot) {
            nodeData.shadowRoot = true;
        }

        // Handle shadow DOM
        if (node.shadowRoot) {
            const shadowChildren = Array.from(node.shadowRoot.childNodes).map(child =>
                buildDomTree(child, parentIframe)
            );
            nodeData.children.push(...shadowChildren);
        }

        // Handle iframes
        if (node.tagName === 'IFRAME') {
            try {
                const iframeDoc = node.contentDocument || node.contentWindow.document;
                if (iframeDoc) {
                    const iframeChildren = Array.from(iframeDoc.body.childNodes).map(child =>
                        buildDomTree(child, node)
                    );
                    nodeData.children.push(...iframeChildren);
                }
            } catch (e) {
                console.warn('Unable to access iframe:', node);
            }
        } else {
            const children = Array.from(node.childNodes).map(child =>
                buildDomTree(child, parentIframe)
            );
            nodeData.children.push(...children);
        }

        return nodeData;
    }


    return buildDomTree(document.body);
}
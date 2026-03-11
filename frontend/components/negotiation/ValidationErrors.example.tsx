/**
 * Example usage of ValidationErrors component with useNegotiationState hook
 * 
 * This file demonstrates how to integrate state validation and error display
 * in a negotiation component.
 */

import React from 'react';
import { useNegotiationState } from '../../hooks/useNegotiationState';
import { ValidationErrors } from './ValidationErrors';

/**
 * Example component showing validation integration
 */
export function NegotiationStateExample() {
  const {
    state,
    validationErrors,
    updateStateFromAI
  } = useNegotiationState();

  // Example: AI updates state with prices
  const handleAIUpdate = () => {
    updateStateFromAI({
      item: 'iPhone 14 Pro',
      target_price: 60000,  // Invalid: exceeds max_price
      max_price: 50000
    });
  };

  return (
    <div className="negotiation-state-example">
      <h2>Negotiation State</h2>
      
      {/* Display current state */}
      <div className="state-display">
        <p>Item: {state.item || 'Not set'}</p>
        <p>Target Price: ₹{state.target_price}</p>
        <p>Max Price: ₹{state.max_price}</p>
      </div>

      {/* Display validation errors */}
      <ValidationErrors errors={validationErrors} />

      {/* Example button to trigger AI update */}
      <button onClick={handleAIUpdate}>
        Simulate AI Update (Invalid Prices)
      </button>

      {/* Show validation status */}
      <div className="validation-status">
        {validationErrors.length === 0 ? (
          <p className="success">✓ State is valid</p>
        ) : (
          <p className="error">✗ State has validation errors</p>
        )}
      </div>
    </div>
  );
}

/**
 * Example: Using validation in a form
 */
export function NegotiationFormExample() {
  const {
    state,
    validationErrors,
    updateStateFromAI
  } = useNegotiationState();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Check if there are validation errors before submitting
    if (validationErrors.length > 0) {
      console.error('Cannot submit: validation errors exist', validationErrors);
      return;
    }

    // Proceed with submission
    console.log('Submitting valid state:', state);
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Negotiation Form</h2>

      {/* Display validation errors at the top */}
      <ValidationErrors errors={validationErrors} />

      {/* Form fields would go here */}
      <div className="form-fields">
        <p>Target Price: ₹{state.target_price}</p>
        <p>Max Price: ₹{state.max_price}</p>
      </div>

      {/* Submit button disabled if there are errors */}
      <button 
        type="submit" 
        disabled={validationErrors.length > 0}
      >
        Submit
      </button>
    </form>
  );
}

import torch
import numpy as np
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from tqdm import tqdm
from typing import List, Dict, Tuple 

class ModelEvaluator:
    def __init__(self, model, tokenizer, device):
        self.model = model.to(device)
        self.tokenizer = tokenizer
        self.device = device
        self.metrics = {
            'accuracy': [],
            'precision': [],
            'recall': [],
            'f1': []
        }
        self.model.eval()
        
    def evaluate_model(self, test_data: List[tuple]):
        """Evaluate model performance on test data."""
        predictions = []
        true_labels = []
        
        correct_token_id = self.tokenizer.encode("correct", add_special_tokens=False)[0]
        incorrect_token_id = self.tokenizer.encode("incorrect", add_special_tokens=False)[0]
        for sample in tqdm(test_data, desc="Evaluating model"):
            prompt, true_label = sample
            print(f"true_label: {true_label}")
            
            messages = [{"role": "user", "content": prompt}]
            formatted_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False)
            print(f"formatted_promt: {formatted_prompt}")
            # Generate prediction
            inputs = self.tokenizer(
                formatted_prompt, 
                return_tensors='pt', 
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=200,
                    num_beams=1,
                    do_sample=True,
                    temperature=0.7,
                    top_p = 0.9,
                    pad_token_id=self.tokenizer.eos_token_id,
                    output_scores=True,
                    return_dict_in_generate=True,
                    renormalize_logits=True
                )
            # logits = output.scores[0][0, [correct_token_id, incorrect_token_id]]
            # probs = torch.nn.functional.softmax(logits, dim=0)
            
            # prediction = probs[0].item() > 0.5 #Threshold
            transition_scores = output.scores
            if transition_scores: #add this to prevent errors if scores is empty.
                print(f"transition_scores shape: {transition_scores[0].shape}") #print the shape of the first tensor in scores.
                print(f"NaN count: {torch.isnan(transition_scores[0]).sum()}") #check the first tensor for nan.
                print(f"Inf count: {torch.isinf(transition_scores[0]).sum()}") #check first tensor for inf.
                print(f"Negative count: {(transition_scores[0] < 0).sum()}") #check first tensor for negatives.
            
            predicted_text = self.tokenizer.decode(output.sequences[0], skip_special_tokens=True)
            predicted_text = predicted_text.split("<|im_end|>")[-1].strip() #Remove <|im_end|> and anything before it
            # print(f"predicted_text: {predicted_text}")
            # Extract binary classification (correct/incorrect) from prediction and true label
            pred_correct = 'correct' in predicted_text.lower()
            true_correct = true_label.lower() == "correct"
            
            predictions.append(pred_correct)
            true_labels.append(true_correct)
        
        # Calculate metrics
        precision, recall, f1, _ = precision_recall_fscore_support(
            true_labels, predictions, average='binary'
        )
        accuracy = np.mean(np.array(predictions) == np.array(true_labels))
        
        # Store metrics
        self.metrics['accuracy'].append(accuracy)
        self.metrics['precision'].append(precision)
        self.metrics['recall'].append(recall)
        self.metrics['f1'].append(f1)
        
        # Generate confusion matrix
        cm = confusion_matrix(true_labels, predictions)
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'confusion_matrix': cm
        }
    
    def get_metric_improvements(self):
        """Calculate metric improvements over training."""
        improvements = {}
        for metric, values in self.metrics.items():
            if len(values) >= 2:
                initial = values[0]
                final = values[-1]
                improvement = ((final - initial) / initial) * 100
                improvements[metric] = improvement
        return improvements

    def generate_resume_bullets(self):
        """Generate resume-worthy bullet points based on model performance."""
        improvements = self.get_metric_improvements()
        
        bullets = []
        
        # Overall performance bullet
        bullets.append(
            f"Developed ML-based exercise form assessment system achieving {self.metrics['accuracy'][-1]*100:.1f}% "
        )
        
        # Improvement bullet
        if improvements:
            max_improvement = max(improvements.values())
            metric = max(improvements, key=improvements.get)
            bullets.append(
                f"Improved model {metric} by {max_improvement:.1f}% through iterative training "
            )
        
        return bullets


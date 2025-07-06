from django import forms


class ChatForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'rows': 3,
            'placeholder': 'Ask me about your finances... (e.g., "Can I afford a $500 vacation?")'
        }),
        max_length=500,
        label=''
    )
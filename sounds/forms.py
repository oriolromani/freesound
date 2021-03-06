#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django import forms
from django.db.models import Q
from django.forms import ModelForm, Textarea, TextInput
from django.conf import settings
from django.utils.translation import ugettext as _
from sounds.models import License, Flag, Pack, Sound
from utils.forms import TagField, HtmlCleaningCharField
from utils.mail import send_mail_template
from utils.forms import CaptchaWidget
import re


class GeotaggingForm(forms.Form):
    remove_geotag = forms.BooleanField(required=False)
    lat = forms.FloatField(min_value=-90, max_value=90, required=False)
    lon = forms.FloatField(min_value=-180, max_value=180, required=False)
    zoom = forms.IntegerField(min_value=11,
                              error_messages={'min_value': "You should zoom in more until you reach at least zoom 11."},
                              required=False)

    def clean(self):
        data = self.cleaned_data

        if not data.get('remove_geotag'):
            lat = data.get('lat', False)
            lon = data.get('lon', False)
            zoom = data.get('zoom', False)

            # second clause is to detect when no values were submitted.
            # otherwise doesn't work in the describe workflow
            if (not (lat and lon and zoom)) and (not (not lat and not lon and not zoom)):
                raise forms.ValidationError('There are missing fields or zoom level is not enough.')

        return data


class SoundDescriptionForm(forms.Form):
    name = forms.CharField(max_length=512, min_length=5,
                           widget=forms.TextInput(attrs={'size': 65, 'class':'inputText'}))
    tags = TagField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 3}),
                    help_text="<br>Separate tags with spaces. Join multi-word tags with dashes. "
                              "For example: field-recording is a popular tag.")
    description = HtmlCleaningCharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 10}))


class RemixForm(forms.Form):
    sources = forms.CharField(min_length=1, widget=forms.widgets.HiddenInput(), required=False)

    def __init__(self, sound, *args, **kwargs):
        self.sound = sound
        super(RemixForm, self).__init__(*args, **kwargs)

    def clean_sources(self):
        sources = re.sub("[^0-9,]", "", self.cleaned_data['sources'])
        sources = re.sub(",+", ",", sources)
        sources = re.sub("^,+", "", sources)
        sources = re.sub(",+$", "", sources)
        if len(sources) > 0:
            sources = set([int(source) for source in sources.split(",")])
        else:
            sources = set()

        return sources

    def save(self):
        new_sources = self.cleaned_data['sources']
        old_sources = set(source["id"] for source in self.sound.sources.all().values("id"))
        try:
            new_sources.remove(self.sound.id)  # stop the universe from collapsing :-D
        except KeyError:
            pass

        for sid in old_sources - new_sources:  # in old but not in new
            try:
                source = Sound.objects.get(id=sid)
                self.sound.sources.remove(source)
                
                # modify remix_group
                send_mail_template(
                    u'Sound removed as remix source', 'sounds/email_remix_update.txt',
                    {'source': source, 'action': 'removed', 'remix': self.sound},
                    None, source.user.email
                )
            except Sound.DoesNotExist:
                pass
            except Exception, e:
                # Report any other type of exception and fail silently
                print ("Problem removing source from remix or sending mail: %s" % e)

        for sid in new_sources - old_sources:  # in new but not in old
            source = Sound.objects.get(id=sid)
            self.sound.sources.add(source)
            try:
                send_mail_template(
                    u'Sound added as remix source', 'sounds/email_remix_update.txt',
                    {'source': source, 'action': 'added', 'remix': self.sound},
                    None, source.user.email
                )
            except Exception, e:
                # Report any exception but fail silently
                print ("Problem sending mail about source added to remix: %s" % e)


class PackChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, pack):
        return pack.name


class PackForm(forms.Form):
    pack = PackChoiceField(label="Change pack or remove from pack:", queryset=Pack.objects.none(), required=False)
    new_pack = HtmlCleaningCharField(widget=forms.TextInput(attrs={'size': 45}),
                                     label="Or fill in the name of a new pack:", required=False, min_length=1)

    def __init__(self, pack_choices, *args, **kwargs):
        super(PackForm, self).__init__(*args, **kwargs)
        self.fields['pack'].queryset = pack_choices.extra(select={'lower_name': 'lower(name)'}).order_by('lower_name')


class PackDescriptionForm(ModelForm):
    
    class Meta:
        model = Pack
        fields = ('description',)
        widgets = {
            'description': Textarea(attrs={'rows': 5, 'cols':60}),
        }


class PackEditForm(ModelForm):
    pack_sounds = forms.CharField(min_length=1,
                                  widget=forms.widgets.HiddenInput(attrs={'id': 'pack_sounds', 'name': 'pack_sounds'}),
                                  required=False)

    def clean_pack_sounds(self):
        pack_sounds = re.sub("[^0-9,]", "", self.cleaned_data['pack_sounds'])
        pack_sounds = re.sub(",+", ",", pack_sounds)
        pack_sounds = re.sub("^,+", "", pack_sounds)
        pack_sounds = re.sub(",+$", "", pack_sounds)
        if len(pack_sounds) > 0:
            pack_sounds = set([int(sound) for sound in pack_sounds.split(",")])
        else:
            pack_sounds = set()
        return pack_sounds

    def save(self, force_insert=False, force_update=False, commit=True):
        pack = super(PackEditForm, self).save(commit=False)
        affected_packs = list()
        affected_packs.append(pack)
        new_sounds = self.cleaned_data['pack_sounds']
        current_sounds = pack.sound_set.all()
        for snd in current_sounds:
            if snd.id not in new_sounds:
                snd.pack = None
                snd.mark_index_dirty(commit=True)
        for snd in new_sounds:
            current_sounds_ids = [s.id for s in current_sounds]
            if snd not in current_sounds_ids:
                sound = Sound.objects.get(id=snd)
                if sound.pack:
                    affected_packs.append(sound.pack)
                sound.pack = pack
                sound.mark_index_dirty(commit=True)
        if commit:
            pack.save()
        for affected_pack in affected_packs:
            affected_pack.process()
        return pack

    class Meta:
        model = Pack
        fields = ('name','description',)
        widgets = {
            'name': TextInput(),
            'description': Textarea(attrs={'rows': 5, 'cols':50}),
        }


class LicenseForm(forms.Form):
    license = forms.ModelChoiceField(queryset=License.objects.filter(is_public=True), required=True, empty_label=None)

    def clean_license(self):
        if self.cleaned_data['license'].abbreviation == "samp+":
            raise forms.ValidationError('We are in the process of slowly removing this license, '
                                        'please choose another one.')
        return self.cleaned_data['license']


class NewLicenseForm(forms.Form):
    license = forms.ModelChoiceField(queryset=License.objects.filter(Q(name__startswith='Attribution') |
                                                                     Q(name__startswith='Creative')), required=True)


class FlagForm(forms.Form):
    email = forms.EmailField(label="Your email", required=True, help_text="Required.",
                             error_messages={'required': 'Required, please enter your email address.', 'invalid': 'Your'
                                             ' email address appears to be invalid, please check if it\'s correct.'})
    reason_type = forms.ChoiceField(choices=Flag.REASON_TYPE_CHOICES,required=True , label='Reason type')
    reason = forms.CharField(widget=forms.Textarea)
    captcha_key = settings.RECAPTCHA_PUBLIC_KEY
    recaptcha_response = forms.CharField(widget=CaptchaWidget)

    def clean_recaptcha_response(self):
        captcha_response = self.cleaned_data.get("recaptcha_response")
        if not captcha_response:
            raise forms.ValidationError(_("Captcha is not correct"))
        return captcha_response

    def save(self):
        f = Flag()
        f.reason_type = self.cleaned_data['reason_type']
        f.reason = self.cleaned_data['reason']
        f.email = self.cleaned_data['email']
        return f
